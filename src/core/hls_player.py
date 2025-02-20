import AVFoundation
import Foundation
import objc
from typing import Optional, Dict, List

#Adding a class to handle HLS streaming using AVFoundation
class HLSPlayer:
    def __init__(self):
        """Initialize AVFoundation player for HLS streaming"""
        self.player = AVFoundation.AVPlayer.alloc().init()
        self.current_item = None
        self.stream_metrics = {
            'current_bitrate': 0,
            'buffer_size': 0,
            'segment_duration': 0
        }
        print("HLSPlayer initialized")
        
    def load_stream(self, url: str) -> bool:
        """
        Load HLS stream from URL
        
        Args:
            url (str): URL of the HLS manifest (.m3u8)
            
        Returns:
            bool: True if stream loaded successfully
        """
        try:
            asset_url = Foundation.NSURL.URLWithString_(url)
            asset = AVFoundation.AVAsset.assetWithURL_(asset_url)
            self.current_item = AVFoundation.AVPlayerItem.playerItemWithAsset_(asset)
            self.player.replaceCurrentItemWithPlayerItem_(self.current_item)
            
            # Setup stream monitoring
            self._setup_bitrate_monitoring()
            print(f"Stream loaded from URL: {url}")
            return True
        except Exception as e:
            print(f"Error loading stream: {e}")
            return False
            
    def _setup_bitrate_monitoring(self):
        """Configure monitoring for adaptive bitrate streaming"""
        # Access AVPlayerItemAccessLogEvent for bitrate information
        self.current_item.addObserver_forKeyPath_options_context_(
            self,
            "accessLog",
            Foundation.NSKeyValueObservingOptionNew,
            None
        )
        print("Bitrate monitoring setup")
    
    def get_available_bitrates(self) -> List[int]:
        """Return list of available bitrates in the stream"""
        if not self.current_item:
            return []
            
        asset = self.current_item.asset()
        variations = asset.availableMediaCharacteristicsWithMediaSelectionOptions()
        return [var.bitrate() for var in variations]
    
    def set_preferred_bitrate(self, bitrate: int):
        """
        Set preferred maximum bitrate for playback
        
        Args:
            bitrate (int): Maximum bitrate in bits per second
        """
        if self.current_item:
            self.player.setPreferredPeakBitRate_(bitrate)
    
    def get_current_stream_info(self) -> Dict:
        """Get current streaming metrics"""
        if not self.current_item:
            return self.stream_metrics
            
        access_log = self.current_item.accessLog()
        if access_log:
            events = access_log.events()
            if events:
                latest_event = events[-1]
                self.stream_metrics.update({
                    'current_bitrate': latest_event.indicatedBitrate(),
                    'buffer_size': latest_event.observedMaxBitrate(),
                    'segment_duration': latest_event.segmentDuration()
                })
        
        return self.stream_metrics

    def start_playback(self):
        """Start or resume playback"""
        if self.player:
            self.player.play()
            print("Playback started. Change the URL to get actual playback.")
    
    def pause_playback(self):
        """Pause playback"""
        if self.player:
            self.player.pause()
            print("Playback paused")
    
    def seek_to_time(self, time_in_seconds: float):
        """
        Seek to specific time in the stream
        
        Args:
            time_in_seconds (float): Time to seek to in seconds
        """
        if self.player:
            time = AVFoundation.CMTimeMakeWithSeconds(time_in_seconds, 1)
            self.player.seekToTime_(time)
            print(f"Seeked to time: {time_in_seconds} seconds")

# Example usage
if __name__ == "__main__":
    player = HLSPlayer()
    url = "https://example.com/path/to/your/manifest.m3u8"
    if player.load_stream(url):
        player.start_playback()