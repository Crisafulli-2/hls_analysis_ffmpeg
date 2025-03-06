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
    from AppKit import NSWindow, NSView, NSRect, NSApp, NSApplication
    from AppKit import NSApplicationActivationPolicyRegular, NSWindowCollectionBehaviorMoveToActiveSpace
    from AppKit import NSButton, NSButtonTypeToggle, NSButtonTypeMomentaryLight, NSFont, NSMakeRect
    from AppKit import NSBezelStyleRounded, NSOnState, NSOffState

# Global registry to keep track of all player instances
_player_registry = []

# Function to clean up all player instances
def cleanup_all_players():
    """Clean up all registered player instances"""
    global _player_registry
    for player in _player_registry:
        try:
            player.cleanup()
        except Exception:
            pass
    _player_registry = []

# Signal handler for graceful termination
def handle_signal(signum, frame):
    """Handle termination signals"""
    print(f"\nReceived signal {signum}, shutting down all players...")
    cleanup_all_players()
    sys.exit(0)

# Set up global signal handlers
signal.signal(signal.SIGINT, handle_signal)
signal.signal(signal.SIGTERM, handle_signal)

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
    # List of most important AVFoundation metrics to look for
    KNOWN_AV_METRICS = [
        # Bitrate metrics
        'indicatedBitrate', 'observedBitrate', 'averageVideoBitrate', 
        'averageAudioBitrate',
        # Duration metrics
        'durationWatched', 'transferDuration', 'startupTime',
        # Stats metrics
        'numberOfSegmentsDownloaded', 'numberOfBytesTransferred',
        'numberOfStalls', 'numberOfServerAddressChanges',
        'numberOfMediaRequests', 'numberOfDroppedVideoFrames',
        # Segment metrics
        'segmentsDownloadedDuration',
        # Server metrics
        'serverAddress', 'playbackSessionID'
    ]
    
    def __init__(self):
        """Initialize AVFoundation player for HLS streaming"""
        if not is_macos:
            print("Error: HLSPlayer requires macOS")
            return
            
        self.player = AVPlayer.alloc().init()
        self.current_item = None
        # Remove hardcoded metrics
        self.stream_metrics = {}
        
        # Track player events for play/pause
        self.player_events = {
            "PlayEvents": [],
            "PauseEvents": []
        }
        
        # For storing discovered metrics
        self.available_metrics = set()
        # Add a flag to track if we're running
        self.is_running = True
        self.is_cleaned_up = False
        
        # Create an observer for notifications
        self.observer = PlayerObserver.alloc().initWithCallback_(self.playback_finished)
        
        # Register this instance
        _player_registry.append(self)
        
        # Create a window for playback
        self.create_player_view()
        print("HLSPlayer initialized")
    
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
            if self in _player_registry:
                _player_registry.remove(self)
                
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        print("Cleanup complete")
    
    def playback_finished(self, notification):
        """Callback for when playback finishes"""
        print("Stream playback completed")
        self.save_metrics_to_json()
    
    def create_control_buttons(self):
        """Create playback control buttons"""
        button_height = 30
        button_width = 90
        spacing = 10
        bottom_margin = 15
        
        # Calculate positions
        window_width = self.window.frame().size.width
        center_x = window_width / 2
        
        # Play button
        play_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x - button_width - spacing, bottom_margin, button_width, button_height)
        )
        play_button.setBezelStyle_(NSBezelStyleRounded)
        play_button.setTitle_("Play")
        play_button.setAction_("playButtonClicked:")
        play_button.setTarget_(self)
        play_button.setFont_(NSFont.boldSystemFontOfSize_(14))
        
        # Pause button
        pause_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x, bottom_margin, button_width, button_height)
        )
        pause_button.setBezelStyle_(NSBezelStyleRounded)
        pause_button.setTitle_("Pause")
        pause_button.setAction_("pauseButtonClicked:")
        pause_button.setTarget_(self)
        pause_button.setFont_(NSFont.boldSystemFontOfSize_(14))
        
        # Stop button
        stop_button = NSButton.alloc().initWithFrame_(
            NSMakeRect(center_x + button_width + spacing, bottom_margin, button_width, button_height)
        )
        stop_button.setBezelStyle_(NSBezelStyleRounded)
        stop_button.setTitle_("Stop")
        stop_button.setAction_("stopButtonClicked:")
        stop_button.setTarget_(self)
        stop_button.setFont_(NSFont.boldSystemFontOfSize_(14))
        
        # Add buttons to the window
        self.window.contentView().addSubview_(play_button)
        self.window.contentView().addSubview_(pause_button)
        self.window.contentView().addSubview_(stop_button)
    
    def playButtonClicked_(self, sender):
        """Handler for play button clicks"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Play button clicked at {timestamp}")
        
        # Record play event
        self.player_events["PlayEvents"].append({
            "time": timestamp,
            "event": "Play button clicked"
        })
        
        self.start_playback()
        
    def pauseButtonClicked_(self, sender):
        """Handler for pause button clicks"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Pause button clicked at {timestamp}")
        
        # Record pause event
        self.player_events["PauseEvents"].append({
            "time": timestamp,
            "event": "Pause button clicked"
        })
        
        self.pause_playback()
        
    def stopButtonClicked_(self, sender):
        """Handler for stop button clicks"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Stop button clicked at {timestamp}")
        
        # Record stop event
        if "StopEvents" not in self.player_events:
            self.player_events["StopEvents"] = []
            
        self.player_events["StopEvents"].append({
            "time": timestamp,
            "event": "Stop button clicked"
        })
        
        self.save_metrics_to_json()
        self.cleanup()
        NSApplication.sharedApplication().terminate_(None)
        
    def create_player_view(self):
        """Create a window to display the video"""
        try:
            # Initialize the application
            NSApplication.sharedApplication()
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            
            # Create a window with extra height for controls
            control_area_height = 60
            window_width = 800
            video_height = 450
            window_height = video_height + control_area_height
            
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSRect((200, 200), (window_width, window_height)),
                15,  # NSTitledWindowMask | NSClosableWindowMask | NSResizableWindowMask | NSMiniaturizableWindowMask
                2,   # NSBackingStoreBuffered
                False
            )
            self.window.setTitle_("HLS Player")
            # Set window to move to active space when activated
            self.window.setCollectionBehavior_(NSWindowCollectionBehaviorMoveToActiveSpace)
            
            # Create a player layer view
            self.player_layer = AVPlayerLayer.playerLayerWithPlayer_(self.player)
            self.player_layer.setFrame_(((0, control_area_height), (window_width, video_height)))
            
            # Add player layer to window content view
            content_view = self.window.contentView()
            self.layer_view = NSView.alloc().initWithFrame_(NSRect((0, control_area_height), (window_width, video_height)))
            self.layer_view.setWantsLayer_(True)
            self.layer_view.layer().addSublayer_(self.player_layer)
            content_view.addSubview_(self.layer_view)
            
            # Add control buttons
            self.create_control_buttons()
            
            # Setup window close notification
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
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
            NSApplication.sharedApplication().terminate_(None)
        
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
            
            # Setup stream monitoring with a timer that fires every 5 seconds
            self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                5.0, self, "timerFired:", None, True
            )
            
            print(f"Stream loaded from URL: {url}")
            
            # Start metrics discovery in a background thread
            threading.Thread(target=self.discover_metrics_with_retries, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Error loading stream: {e}")
            return False
    
    def discover_metrics_with_retries(self, max_attempts=5, delay=2):
        """Try to discover metrics multiple times with delays"""
        attempts = 0
        
        while self.is_running and attempts < max_attempts and not self.available_metrics:
            print(f"Attempting metrics discovery ({attempts+1}/{max_attempts})...")
            self.discover_available_metrics()
            
            if self.available_metrics:
                print(f"Metrics discovered successfully! Available: {', '.join(sorted(self.available_metrics))}")
                break
                
            attempts += 1
            
            if attempts < max_attempts and self.is_running:
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
            if access_log and access_log.events() and len(access_log.events()) > 0:
                latest_event = access_log.events()[-1]
                
                # Check each metric in our known list
                for method in self.KNOWN_AV_METRICS:
                    if hasattr(latest_event, method) and callable(getattr(latest_event, method)):
                        try:
                            value = getattr(latest_event, method)()
                            if value is not None:
                                self.available_metrics.add(method)
                        except Exception:
                            pass
                
                print(f"Discovered {len(self.available_metrics)} available metrics")
            else:
                print("No access log events found yet")
        except Exception as e:
            print(f"Error discovering metrics: {e}")
        
        return self.available_metrics
    
    def timerFired_(self, timer):
        """Called when the timer fires to update metrics"""
        if not self.is_running:
            return
            
        try:
            # Get current stream info and print metrics report
            self.get_current_stream_info()
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
            video_tracks = asset.tracksWithMediaType_("vide")
            
            for track in video_tracks:
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
            if access_log and access_log.events() and len(access_log.events()) > 0:
                latest_event = access_log.events()[-1]
                
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
                    except Exception:
                        pass
                
                # Update our metrics
                self.stream_metrics.update(metrics)
        except Exception:
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
        for category_name, metric_names in categories.items():
            metrics_in_category = [m for m in metric_names if m in info]
            
            if metrics_in_category:
                report += f"\n{category_name}:\n"
                for metric in metrics_in_category:
                    value = info[metric]
                    # Format bitrates as Mbps
                    if 'bitrate' in metric.lower() and isinstance(value, (int, float)) and value > 1000:
                        report += f"  ├─ {metric}: {value/1000000:.3f} Mbps\n"
                    else:
                        report += f"  ├─ {metric}: {value}\n"
        
        # Add player events if any exist
        if hasattr(self, 'player_events') and (self.player_events["PlayEvents"] or self.player_events["PauseEvents"]):
            report += "\nPlayer Events:\n"
            
            if self.player_events["PlayEvents"]:
                report += "  ├─ Play Events:\n"
                for event in self.player_events["PlayEvents"][-2:]:  # Show only last 2 events
                    report += f"  │  ├─ {event['time']}: {event['event']}\n"
                    
            if self.player_events["PauseEvents"]:
                report += "  ├─ Pause Events:\n"
                for event in self.player_events["PauseEvents"][-2:]:  # Show only last 2 events
                    report += f"  │  ├─ {event['time']}: {event['event']}\n"
        
        # Add any metrics that didn't fit into categories
        uncategorized_metrics = [m for m in info if not any(m in category_metrics 
                                                for category_metrics in categories.values())]
        if uncategorized_metrics:
            report += "\nOther Metrics:\n"
            for metric in sorted(uncategorized_metrics):
                value = info[metric]
                report += f"  ├─ {metric}: {value}\n"
                
        return report
    def get_metrics_as_json(self) -> Dict:
        """
        Get the metrics in a properly structured JSON-friendly format
        
        Returns:
            Dict containing categorized metrics ready for JSON serialization
        """
        # Get current stream info
        info = self.get_current_stream_info()
        
        # Create structured output with categories
        structured_metrics = {
            "Bitrate": {},
            "Duration": {},
            "Statistics": {},
            "Server": {}
        }
        
        # Define metric categories
        categories = {
            'Bitrate': ['indicatedBitrate', 'indicatedAverageBitrate', 'observedBitrate', 
                       'averageVideoBitrate', 'averageAudioBitrate'],
            'Duration': ['durationWatched', 'transferDuration', 'startupTime', 
                        'segmentsDownloadedDuration'],
            'Statistics': ['numberOfSegmentsDownloaded', 'numberOfBytesTransferred',
                          'numberOfStalls', 'numberOfServerAddressChanges',
                          'numberOfMediaRequests', 'numberOfDroppedVideoFrames'],
            'Server': ['serverAddress', 'playbackSessionID']
        }
        
        # Categorize metrics
        for key, value in info.items():
            # Find which category this metric belongs to
            assigned = False
            for category, metrics in categories.items():
                if key in metrics:
                    # Convert bitrates to Mbps for readability
                    if 'bitrate' in key.lower() and isinstance(value, (int, float)) and value > 1000:
                        structured_metrics[category][key] = round(value / 1000000, 3)
                    else:
                        structured_metrics[category][key] = value
                    assigned = True
                    break
            
            # If not assigned to any category, put in Other
            if not assigned:
                if "Other" not in structured_metrics:
                    structured_metrics["Other"] = {}
                structured_metrics["Other"][key] = value
        
        # Add computed metrics
        if 'numberOfStalls' in info:
            structured_metrics['Statistics']['BufferingEvents'] = info['numberOfStalls']
            
        if 'startupTime' in info:
            structured_metrics['Duration']['InitialBufferingTime'] = round(info['startupTime'], 2)
        
        # Add player event tracking metrics
        if hasattr(self, 'player_events') and (
            self.player_events["PlayEvents"] or 
            self.player_events["PauseEvents"]
        ):
            structured_metrics['PlayerEvents'] = {
                "PlayCount": len(self.player_events["PlayEvents"]),
                "PauseCount": len(self.player_events["PauseEvents"]),
                "PlayEvents": self.player_events["PlayEvents"],
                "PauseEvents": self.player_events["PauseEvents"]
            }
        
        # Remove empty categories
        return {k: v for k, v in structured_metrics.items() if v}
        
    def save_metrics_to_json(self):
        """Save the current metrics to the analysis_output.json file with proper structure"""
        if not self.available_metrics and not hasattr(self, 'player_events'):
            print("No metrics available to save")
            return
            
        try:
            # Get the path to the output JSON file
            output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 
                                      'output', 'analysis_output.json')
            
            print(f"Saving metrics to {output_path}")
            
            # Get metrics in structured format
            av_metrics = self.get_metrics_as_json()
            
            # Read the existing JSON file
            try:
                with open(output_path, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}
            
            # Update the AVFoundation metrics section with structured data
            data['AVFoundation_Metrics'] = av_metrics
            
            # Write the updated data back to the file with indentation
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

def main():
    if not is_macos:
        print("This player requires macOS to run")
        return
        
    # Get URL from config.json or use default
    try:
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config.json')
        with open(config_path, 'r') as config_file:
            config = json.load(config_file)
            url = config.get('m3u8_url')
            if not url:
                raise ValueError("No m3u8_url found in config.json")
    except Exception:
        # Use a reliable default
        url = "https://demo.unified-streaming.com/k8s/features/stable/video/tears-of-steel/tears-of-steel.ism/.m3u8"
    
    print(f"Using URL: {url}")
    
    player = HLSPlayer()
    if player.load_stream(url):
        player.start_playback()
        
        # Display some info after a short delay
        time.sleep(2)
        
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