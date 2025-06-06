import ipfshttpclient
import json
import logging
import time
import os
from typing import Optional, Dict, Any, Union
from pathlib import Path
from datetime import datetime

class IPFSHandler:
    def __init__(self, host: Optional[str] = None, 
                 timeout: int = 30, retries: int = 3, 
                 retry_delay: int = 2):
        """
        Enhanced IPFS handler with configurable connection settings
        
        Args:
            host: IPFS API endpoint (if None, reads from IPFS_HOST env var)
            timeout: Operation timeout in seconds
            retries: Connection retry attempts
            retry_delay: Delay between retries in seconds
        """
        # Use environment variable if host not provided
        if host is None:
            host = os.getenv('IPFS_HOST', '/ip4/ipfs/tcp/5001')
        
        self.host = host
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self.client = None
        self._setup_logger()
        self._connect()

    def _connect(self) -> None:
        """Establish connection with retry logic"""
        for attempt in range(1, self.retries + 1):
            try:
                self.client = ipfshttpclient.connect(
                    self.host,
                    timeout=self.timeout,
                    session=True
                )
                # Verify connection by getting node ID
                node_id = self.client.id()['ID']
                self.logger.info(f"Connected to IPFS node {node_id} at {self.host}")
                return
            except Exception as e:
                self.logger.warning(f"Connection attempt {attempt}/{self.retries} failed: {str(e)}")
                if attempt < self.retries:
                    time.sleep(self.retry_delay)
        
        self.logger.error(f"All connection attempts to IPFS failed for host: {self.host}")
        self.client = None
    def _setup_logger(self) -> None:
        """Configure advanced logging"""
        self.logger = logging.getLogger('IPFSHandler')
        self.logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.WARNING)
        
        # File handler
        fh = logging.FileHandler('ipfs_handler.log')
        fh.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        self.logger.addHandler(ch)
        self.logger.addHandler(fh)

    def _ensure_connection(self) -> bool:
        """Verify we have an active connection"""
        if not self.client:
            self.logger.warning("No active IPFS connection, attempting to reconnect...")
            self._connect()
            return bool(self.client)
        return True

    def add_file(self, file_path: Union[str, Path], pin: bool = True) -> Optional[str]:
        """
        Upload file to IPFS with enhanced error handling
        
        Args:
            file_path: Path to file (str or Path object)
            pin: Whether to pin the content
            
        Returns:
            IPFS CID or None if failed
        """
        if not self._ensure_connection():
            return None

        path = str(file_path)
        try:
            # Verify file exists first
            if not Path(path).exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            res = self.client.add(
                path,
                timeout=self.timeout,
                pin=pin,
                recursive=False
            )
            
            cid = res['Hash']
            self.logger.info(f"Added file {path} as CID: {cid}")
            
            if pin:
                self.ensure_pinned(cid)
                
            return cid
            
        except Exception as e:
            self.logger.error(f"Failed to add file {path}: {str(e)}")
            return None

    def add_json(self, data: Dict[str, Any], pin: bool = True) -> Optional[str]:
        """
        Upload JSON data with metadata tracking
        
        Args:
            data: JSON-serializable data
            pin: Whether to pin the content
            
        Returns:
            IPFS CID or None if failed
        """
        if not self._ensure_connection():
            return None
            
        try:
            # Add metadata to the stored data
            enhanced_data = {
                'data': data,
                'metadata': {
                    'created': datetime.utcnow().isoformat(),
                    'source': 'voting_system'
                }
            }
            
            json_str = json.dumps(enhanced_data)
            cid = self.client.add_str(json_str, timeout=self.timeout, pin=pin)
            
            self.logger.info(f"Added JSON data as CID: {cid}")
            
            if pin:
                self.ensure_pinned(cid)
                
            return cid
            
        except Exception as e:
            self.logger.error(f"Failed to add JSON data: {str(e)}")
            return None

    def get_json(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve JSON data with validation
        
        Args:
            ipfs_hash: CID to retrieve
            
        Returns:
            Deserialized JSON or None if failed
        """
        if not self._ensure_connection():
            return None
            
        try:
            # Verify hash format
            if not self._validate_cid(ipfs_hash):
                raise ValueError(f"Invalid IPFS hash: {ipfs_hash}")
            
            data = self.client.cat(ipfs_hash, timeout=self.timeout)
            result = json.loads(data)
            
            # Validate structure
            if 'data' not in result:
                raise ValueError("Retrieved data has invalid format")
                
            return result['data']
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve JSON {ipfs_hash}: {str(e)}")
            return None

    def ensure_pinned(self, ipfs_hash: str) -> bool:
        """
        Robust pinning with verification
        
        Args:
            ipfs_hash: CID to pin
            
        Returns:
            True if pinned successfully
        """
        if not self._ensure_connection():
            return False
            
        try:
            # First verify the content exists
            self.client.cat(ipfs_hash, timeout=10)
            
            # Check pin status
            pins = self.client.pin.ls(
                ipfs_hash,
                timeout=self.timeout,
                type='recursive'
            )
            
            if ipfs_hash not in pins:
                self.client.pin.add(
                    ipfs_hash,
                    timeout=self.timeout,
                    recursive=False
                )
                self.logger.info(f"Pinned content: {ipfs_hash}")
                
            # Verify pin was successful
            pins = self.client.pin.ls(ipfs_hash)
            return ipfs_hash in pins
            
        except ipfshttpclient.exceptions.Error as e:
            self.logger.error(f"Pinning failed for {ipfs_hash}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during pinning {ipfs_hash}: {str(e)}")
            return False

    def _validate_cid(self, cid: str) -> bool:
        """Basic CID validation"""
        return (isinstance(cid, str) and 
                len(cid) >= 10 and 
                cid.startswith('Qm'))

    def check_connection(self) -> bool:
        """Verify active connection to IPFS node"""
        if not self.client:
            return False
        try:
            return bool(self.client.id(timeout=5))
        except:
            return False

    def get_pin_status(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed pin status
        
        Args:
            ipfs_hash: CID to check
            
        Returns:
            Pin status dict or None if failed
        """
        if not self._ensure_connection():
            return None
            
        try:
            return self.client.pin.ls(
                ipfs_hash,
                timeout=self.timeout,
                type='all'
            )
        except Exception as e:
            self.logger.warning(f"Failed to get pin status for {ipfs_hash}: {str(e)}")
            return None


# Example usage remains the same
if __name__ == "__main__":
    # Initialize handler
    ipfs_handler = IPFSHandler()
    
    # Test with sample vote data
    vote_data = {
        "election_id": "12345",
        "voter_id": "67890",
        "candidate_id": "1",
        "timestamp": "2025-05-23T12:00:00Z",
        "signature": "0xabc123..."
    }
    
    # Store vote in IPFS
    cid = ipfs_handler.add_json(vote_data)
    if cid:
        print(f"Vote stored with CID: {cid}")
        
        # Retrieve vote
        retrieved = ipfs_handler.get_json(cid)
        print("Retrieved vote data:", retrieved)
        
        # Verify pin
        if ipfs_handler.ensure_pinned(cid):
            print("Vote is securely pinned in IPFS")
            print("Pin status:", ipfs_handler.get_pin_status(cid))
        else:
            print("Warning: Vote could not be pinned")
    else:
        print("Failed to store vote in IPFS")