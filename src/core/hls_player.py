#!/usr/bin/env python3
"""
HLS Player - macOS native HLS video player using AVFoundation

This module provides a native macOS HLS video player that can be used to:
1. Play HLS (HTTP Live Streaming) content
2. Monitor streaming metrics like bitrate
3. Control playback (play, pause, seek)

Requires PyObjC and macOS.
"""

import sys
import time
import os
import json
import signal
import threading
from typing import Optional, Dict, List, Any, Set

# Check if running on macOS
is_macos = sys.platform == 'darwin'

if is_macos:
    # Import PyObjC modules only on macOS
    import objc
    from Foundation import NSURL, NSObject, NSNotificationCenter, NSTimer
    # Load the required frameworks
    objc.loadBundle('AVFoundation', globals(), 
                   bundle_path=objc.pathForFramework('/System/Library/Frameworks/AVFoundation.framework'))
    objc.loadBundle('CoreMedia', globals(), 
                   bundle_path=objc.pathForFramework('/System/Library/Frameworks/CoreMedia.framework'))
    from AVFoundation import AVPlayer, AVPlayerItem, AVAsset, AVPlayerLayer
else:
    print("Warning: macOS is required for native AVFoundation HLS player")

# Global registry to keep track of all player instances
_player_registry = []

# Function to clean up all player instances
def cleanup_all_players():
    """Clean up all registered player instances"""
    global _player_registry
    for player in _player_registry:
        try:
            player.cleanup()
        except:
            pass
    _player_registry = []

# Register global signal handlers
def setup_global_signal_handlers():
    """Set up global handlers for termination signals"""
    if is_macos:
        signal.signal(signal.SIGINT, handle_global_signal)
        signal.signal(signal.SIGTERM, handle_global_signal)

def handle_global_signal(signum, frame):
    """Global handler for termination signals"""
    print(f"\nReceived signal {signum}, shutting down all players...")
    cleanup_all_players()
    sys.exit(0)

# Set up global handlers
setup_global_signal_handlers()

# Create an observer class to handle notifications properly
if is_macos:
    class PlayerObserver(NSObject):
        def initWithCallback_(self, callback):
            self = objc.super(PlayerObserver, self).init()
            if self is None: return None
            self.callback = callback
            return self
            
        def playerItemDidPlayToEndTime_(self, notification):
            self.callback(notification)

class HLSPlayer:
    # List of known useful AVFoundation metrics to look for
    KNOWN_AV_METRICS = [
        # Bitrate metrics
        'indicatedBitrate', 'indicatedAverageBitrate', 'observedBitrate', 
        'observedMaxBitrate', 'observedMinBitrate', 'averageVideoBitrate', 
        'averageAudioBitrate', 'observedBitrateStandardDeviation',
        # Duration metrics
        'durationWatched', 'transferDuration', 'startupTime',
        # Stats metrics
        'numberOfSegmentsDownloaded', 'numberOfBytesTransferred',
        'numberOfStalls', 'numberOfServerAddressChanges',
        'numberOfMediaRequests', 'numberOfDroppedVideoFrames',
        # Segment metrics
        'segmentsDownloadedDuration', 'playbackType',
        # Server metrics
        'serverAddress', 'URI', 'playbackSessionID'
    ]
    
    def __init__(self):
        """Initialize AVFoundation player for HLS streaming"""
        if not is_macos:
            print("Error: HLSPlayer requires macOS")
            return
            
        self.player = AVPlayer.alloc().init()
        self.current_item = None
        self.stream_metrics = {
            'current_bitrate': 0,
            'buffer_size': 0,
            'segments_loaded': 0
        }
        
        # For storing discovered metrics
        self.available_metrics = set()
        # Add a flag to track if we're running
        self.is_running = True
        self.is_cleaned_up = False
        
        # Create an observer for notifications
        self.observer = PlayerObserver.alloc().initWithCallback_(self.playback_finished)
        
        # Register this instance
        global _player_registry
        _player_registry.append(self)
        
        # Create a window for playback
        self.create_player_view()
        print("HLSPlayer initialized")
        
        # Set up signal handlers for clean termination
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Set up handlers for termination signals"""
        # Note: Global handlers are already set up
        pass
        
    def cleanup(self):
        """Clean up resources properly to avoid spinning wheel issues"""
        if self.is_cleaned_up:  # Prevent duplicate cleanup
            return
            
        print("Cleaning up resources...")
        self.is_running = False
        self.is_cleaned_up = True
        
        try:
            # First, save metrics to JSON if we have any
            if self.available_metrics:
                self.save_metrics_to_json()
                
            # Stop timer first
            if hasattr(self, 'timer') and self.timer:
                self.timer.invalidate()
                self.timer = None
                
            # Stop and remove any notification observers
            if is_macos:
                NSNotificationCenter.defaultCenter().removeObserver_(self)
            
            # Explicitly remove player layer
            if hasattr(self, 'player_layer') and self.player_layer:
                self.player_layer.setPlayer_(None)
                
            # Stop playback and clear the player
            if self.player:
                self.player.pause()
                self.player.replaceCurrentItemWithPlayerItem_(None)
                self.player = None
            
            self.current_item = None
            
            # Close window if available
            if hasattr(self, 'window') and self.window:
                self.window.close()
                self.window = None
                
            # Remove from registry
            global _player_registry
            if self in _player_registry:
                _player_registry.remove(self)
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        print("Cleanup complete")
    
    def playback_finished(self, notification):
        """Callback for when playback finishes"""
        print("Stream playback completed")
        self.save_metrics_to_json()
        
    def create_player_view(self):
        """Create a window to display the video"""
        try:
            # Import AppKit for UI elements
            from AppKit import NSWindow, NSView, NSRect, NSApp, NSApplication
            from AppKit import NSApplicationActivationPolicyRegular, NSWindowCollectionBehaviorMoveToActiveSpace
            
            # Initialize the application
            NSApplication.sharedApplication()
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            
            # Create a window
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSRect((200, 200), (800, 450)),  # Position and size - 16:9 aspect ratio
                15,  # NSTitledWindowMask | NSClosableWindowMask | NSResizableWindowMask | NSMiniaturizableWindowMask
                2,   # NSBackingStoreBuffered
                False
            )
            self.window.setTitle_("HLS Player")
            # Set window to move to active space when activated
            self.window.setCollectionBehavior_(NSWindowCollectionBehaviorMoveToActiveSpace)
            
            # Create a player layer view
            self.player_layer = AVPlayerLayer.playerLayerWithPlayer_(self.player)
            self.player_layer.setFrame_(((0, 0), (800, 450)))
            
            # Get the window's content view
            content_view = self.window.contentView()
            self.layer_view = NSView.alloc().initWithFrame_(NSRect((0, 0), (800, 450)))
            self.layer_view.setWantsLayer_(True)
            self.layer_view.layer().addSublayer_(self.player_layer)
            content_view.addSubview_(self.layer_view)
            
            # Setup window close notification
            nc = NSNotificationCenter.defaultCenter()
            nc.addObserver_selector_name_object_(
                self,
                "windowWillClose:",
                "NSWindowWillCloseNotification",
                self.window
            )
            
            # Make the window visible
            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)
            
        except Exception as e:
            print(f"Error creating player view: {e}")
    
    def windowWillClose_(self, notification):
        """Handle window closing with proper cleanup"""
        print("Window is closing, cleaning up...")
        self.save_metrics_to_json()
        
        # Schedule cleanup to run after this method returns
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.1,  # Short delay to let the close animation finish
            self,
            "performTermination:",
            None,
            False
        )

    def performTermination_(self, timer):
        """Perform actual termination after a short delay"""
        self.cleanup()
        
        # If this is the last player instance, terminate the application
        if not _player_registry:
            from AppKit import NSApplication
            NSApplication.sharedApplication().terminate_(None)
            
            # Force quit after a delay if normal termination doesn't work
            from Foundation import NSProcessInfo
            import os
            pid = NSProcessInfo.processInfo().processIdentifier()
            threading.Timer(1.0, lambda: os.system(f"kill -TERM {pid}")).start()
        
    def load_stream(self, url: str) -> bool:
        """
        Load HLS stream from URL
        
        Args:
            url (str): URL of the HLS manifest (.m3u8)
            
        Returns:
            bool: True if stream loaded successfully
        """
        if not is_macos:
            print("Error: HLSPlayer requires macOS")
            return False
            
        try:
            asset_url = NSURL.URLWithString_(url)
            asset = AVAsset.assetWithURL_(asset_url)
            self.current_item = AVPlayerItem.playerItemWithAsset_(asset)
            self.player.replaceCurrentItemWithPlayerItem_(self.current_item)
            
            # Setup stream monitoring
            self._setup_monitoring()
            print(f"Stream loaded from URL: {url}")
            
            # Start metrics discovery in a background thread
            threading.Thread(target=self.discover_metrics_with_retries, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Error loading stream: {e}")
            return False
    
    def discover_metrics_with_retries(self, max_attempts=10, delay=2):
        """Try to discover metrics multiple times with delays"""
        attempts = 0
        
        while self.is_running and attempts < max_attempts and not self.available_metrics:
            print(f"Attempting metrics discovery ({attempts+1}/{max_attempts})...")
            self.discover_available_metrics()
            
            if self.available_metrics:
                print("Metrics discovered successfully!")
                print(f"Available HLS metrics: {', '.join(sorted(self.available_metrics))}")
                break
                
            attempts += 1
            
            if attempts < max_attempts and self.is_running:
                print(f"Waiting {delay} seconds before next attempt...")
                time.sleep(delay)
    
    def discover_available_metrics(self) -> Set[str]:
        """
        Discover what metrics are available in this version of macOS
        
        Returns:
            Set of available metric names
        """
        if not is_macos or not self.current_item or not self.is_running:
            return set()
        
        try:
            access_log = self.current_item.accessLog()
            if access_log:
                events = access_log.events()
                if events and len(events) > 0:
                    latest_event = events[-1]
                    
                    # Only try our known AV metrics instead of every method
                    for method in self.KNOWN_AV_METRICS:
                        try:
                            # Get the method object
                            if hasattr(latest_event, method):
                                method_obj = getattr(latest_event, method)
                                
                                # Check if it's callable
                                if callable(method_obj):
                                    # Try calling it
                                    value = method_obj()
                                    print(f"AV Metric {method} returned: {value}")
                                    if value is not None:
                                        self.available_metrics.add(method)
                        except Exception as e:
                            # Silently skip this one
                            pass
                    
                    print(f"Discovered {len(self.available_metrics)} available metrics")
                else:
                    print("No access log events found yet")
            else:
                print("No access log available yet")
        except Exception as e:
            print(f"Error discovering metrics: {e}")
        
        return self.available_metrics
            
    def _setup_monitoring(self):
        """Configure monitoring for adaptive bitrate streaming"""
        if not self.current_item:
            return
            
        # For simplicity, use a timer-based approach instead of notification
        # This avoids issues with PyObjC selector/notification handling
        
        # Create a timer that fires every 5 seconds
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            5.0,          # Interval in seconds
            self,         # Target (self)
            "timerFired:", # Selector
            None,         # User info (None)
            True          # Repeats
        )
        
        print("Set up periodic stream monitoring")
    
    def timerFired_(self, timer):
        """Called when the timer fires"""
        if not self.is_running:
            return
            
        try:
            # Get current stream info
            info = self.get_current_stream_info()
            
            # Print current metrics report
            print("\n" + self.get_all_metrics_report())
        except Exception as e:
            print(f"Error in timer: {e}")
    
    def get_available_bitrates(self) -> List[int]:
        """Return list of available bitrates in the stream"""
        if not is_macos or not self.current_item or not self.is_running:
            return []
            
        bitrates = []
        try:
            asset = self.current_item.asset()
            # Get video tracks
            video_tracks = asset.tracksWithMediaType_("vide")
            
            for track in video_tracks:
                # Get track's video parameters
                format_descriptions = track.formatDescriptions()
                if format_descriptions and len(format_descriptions) > 0:
                    format_desc = format_descriptions[0]
                    if hasattr(format_desc, "mediaSpecific"):
                        format_dict = format_desc.mediaSpecific()
                        if format_dict and 'AvgBitRate' in format_dict:
                            bitrates.append(format_dict['AvgBitRate'])
        except Exception as e:
            print(f"Error getting available bitrates: {e}")
            
        return bitrates
    
    def set_preferred_bitrate(self, bitrate: int):
        """
        Set preferred maximum bitrate for playback
        
        Args:
            bitrate (int): Maximum bitrate in bits per second
        """
        if is_macos and self.player and self.is_running:
            self.player.setPreferredPeakBitRate_(bitrate)
    
    def get_current_stream_info(self) -> Dict:
        """
        Get current streaming metrics using dynamically discovered methods
        
        Returns:
            Dict containing available streaming metrics
        """
        if not is_macos or not self.current_item or not self.is_running:
            return self.stream_metrics
            
        try:
            access_log = self.current_item.accessLog()
            if access_log:
                events = access_log.events()
                if events and len(events) > 0:
                    latest_event = events[-1]
                    
                    # Process each discovered metric
                    metrics = {}
                    
                    # Add all available metrics we've discovered
                    for metric in self.available_metrics:
                        try:
                            method_obj = getattr(latest_event, metric)
                            value = method_obj()
                            # Only add non-None values
                            if value is not None:
                                metrics[metric] = value
                        except:
                            pass
                    
                    # Update our metrics
                    self.stream_metrics.update(metrics)
        except Exception as e:
            pass
        
        return self.stream_metrics

    def start_playback(self):
        """Start or resume playback"""
        if is_macos and self.player and self.is_running:
            self.player.play()
            print("Playback started")
    
    def pause_playback(self):
        """Pause playback"""
        if is_macos and self.player and self.is_running:
            self.player.pause()
            print("Playback paused")
    
    def seek_to_time(self, time_in_seconds: float):
        """
        Seek to specific time in the stream
        
        Args:
            time_in_seconds (float): Time to seek to in seconds
        """
        if is_macos and self.player and self.is_running:
            # Create CMTime for seeking
            time_scale = 1000  # Higher precision
            try:
                target_time = objc.lookUpClass("CMTimeMake")(int(time_in_seconds * time_scale), time_scale)
                self.player.seekToTime_(target_time)
                print(f"Seeked to time: {time_in_seconds} seconds")
            except Exception as e:
                print(f"Error seeking: {e}")
    
    def get_all_metrics_report(self) -> str:
        """Get a formatted report of all available metrics"""
        if not self.available_metrics:
            return "No metrics available yet. Still discovering..."
            
        info = self.get_current_stream_info()
        report = "== HLS Stream Metrics ==\n"
        
        # Categorize metrics for better readability
        categories = {
            'Bitrate': ['indicatedBitrate', 'indicatedAverageBitrate', 'observedBitrate', 
                       'observedMaxBitrate', 'observedMinBitrate', 'averageVideoBitrate', 
                       'averageAudioBitrate', 'observedBitrateStandardDeviation'],
            'Duration': ['durationWatched', 'transferDuration', 'startupTime', 
                        'segmentsDownloadedDuration'],
            'Statistics': ['numberOfSegmentsDownloaded', 'numberOfBytesTransferred',
                          'numberOfStalls', 'numberOfServerAddressChanges',
                          'numberOfMediaRequests', 'numberOfDroppedVideoFrames'],
            'Server': ['serverAddress', 'URI', 'playbackSessionID', 'playbackType']
        }
        
        # Print metrics by category
        for category, metric_names in categories.items():
            # Check if we have any metrics in this category
            has_metrics = any(metric in info for metric in metric_names)
            
            if has_metrics:
                report += f"\n{category}:\n"
                for metric in metric_names:
                    if metric in info:
                        value = info[metric]
                        # Format bitrates as Mbps
                        if 'bitrate' in metric.lower() and isinstance(value, (int, float)) and value > 1000:
                            report += f"  {metric}: {value/1000000:.3f} Mbps\n"
                        else:
                            report += f"  {metric}: {value}\n"
        
        # Add any metrics that didn't fit into categories
        other_metrics = [m for m in info if not any(m in category_metrics 
                                                 for category_metrics in categories.values())]
        if other_metrics:
            report += "\nOther Metrics:\n"
            for metric in sorted(other_metrics):
                value = info[metric]
                report += f"  {metric}: {value}\n"
                
        return report

    def get_metrics_as_json(self) -> Dict:
        """
        Get the metrics in a JSON-friendly format with proper conversions
        
        Returns:
            Dict containing metrics ready for JSON serialization
        """
        info = self.get_current_stream_info()
        metrics = {}
        
        # Process all metrics into a suitable format for JSON
        for key, value in info.items():
            # Convert bitrates to Mbps
            if 'bitrate' in key.lower() and isinstance(value, (int, float)) and value > 1000:
                metrics[key] = round(value / 1000000, 3)  # To Mbps with 3 decimal places
            else:
                metrics[key] = value
        
        # Add some computed/aggregated metrics
        if 'numberOfStalls' in metrics:
            metrics['BufferingEvents'] = metrics['numberOfStalls']
            
        if 'startupTime' in metrics:
            metrics['InitialBufferingTime'] = round(metrics['startupTime'], 2)
        
        return metrics
        
    def save_metrics_to_json(self):
        """Save the current metrics to the analysis_output.json file"""
        if not self.available_metrics:
            print("No metrics available to save")
            return
            
        try:
            # Get the path to the output JSON file in the output directory
            output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      'output', 'analysis_output.json')
            
            print(f"Saving metrics to {output_path}")
            
            # Get metrics in JSON-friendly format
            av_metrics = self.get_metrics_as_json()
            
            # Read the existing JSON file
            try:
                with open(output_path, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                # If file doesn't exist or is invalid, create a new data structure
                data = {}
            
            # Add or update the AVFoundation metrics section
            data['AVFoundation_Metrics'] = av_metrics
            
            # Write the updated data back to the file
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=4)
            
            print("Metrics saved to JSON file")
        except Exception as e:
            print(f"Error saving metrics to JSON: {e}")
    
    def applicationWillTerminate_(self, notification):
        """Handle application termination notification"""
        print("Application is terminating...")
        self.save_metrics_to_json()
        self.cleanup()
    
    def run_app_loop(self):
        """Run the application event loop with improved termination handling"""
        if is_macos:
            try:
                from AppKit import NSApplication
                
                # Set an AppKit terminate notification handler
                NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                    self,
                    "applicationWillTerminate:",
                    "NSApplicationWillTerminateNotification",
                    None
                )
                
                # Run the application
                NSApplication.sharedApplication().run()
            except KeyboardInterrupt:
                print("\nKeyboard interrupt received, shutting down...")
                self.save_metrics_to_json()
                self.cleanup()
            except Exception as e:
                print(f"Error in app loop: {e}")
                self.cleanup()

# Example usage
def main():
    if not is_macos:
        print("This player requires macOS to run")
        return
        
    # Get URL from config.json or use default
    import json
    import os
    
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            url = config.get('m3u8_url')
            if not url:
                raise ValueError("No m3u8_url found in config.json")
    except Exception as e:
        print(f"Error loading config: {e}")
        # Use a reliable default
        url = "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8"
    
    print(f"Using URL: {url}")
    
    player = HLSPlayer()
    if player.load_stream(url):
        player.start_playback()
        
        # Display some info after a short delay
        time.sleep(3)  # Give time for stream to initialize
        
        # Try to get bitrates
        bitrates = player.get_available_bitrates()
        if bitrates:
            print(f"Available bitrates: {[b/1000000 for b in bitrates]} Mbps")
        
        try:
            # Run the app loop for UI
            player.run_app_loop()
        except KeyboardInterrupt:
            print("\nKeyboard interrupt received. Shutting down...")
            player.save_metrics_to_json()
        finally:
            player.cleanup()
            # Ensure all players are cleaned up
            cleanup_all_players()
    
    print("HLS Player terminated")

if __name__ == "__main__":
    main()