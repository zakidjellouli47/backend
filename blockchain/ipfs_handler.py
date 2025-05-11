import ipfshttpclient
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

class IPFSHandler:
    def __init__(self):
        self.client = self._connect_to_ipfs()
        self.logger = self._setup_logger()

    def _connect_to_ipfs(self):
        """Establish connection to IPFS daemon"""
        try:
            return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        except Exception as e:
            logging.error(f"Failed to connect to IPFS: {str(e)}")
            return None

    def _setup_logger(self):
        logger = logging.getLogger('IPFSHandler')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    def add_file(self, file_path: str) -> Optional[str]:
        """Upload file to IPFS"""
        if not self.client:
            return None
        
        try:
            res = self.client.add(file_path)
            self.client.pin.add(res['Hash'])
            return res['Hash']
        except Exception as e:
            self.logger.error(f"Failed to add file: {str(e)}")
            return None

    def add_json(self, data: Dict[str, Any]) -> Optional[str]:
        """Upload JSON data to IPFS"""
        if not self.client:
            return None
            
        try:
            json_str = json.dumps(data)
            res = self.client.add_str(json_str)
            self.client.pin.add(res)
            return res
        except Exception as e:
            self.logger.error(f"Failed to add JSON: {str(e)}")
            return None

    def get_json(self, ipfs_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieve JSON data from IPFS"""
        if not self.client:
            return None
            
        try:
            data = self.client.cat(ipfs_hash)
            return json.loads(data)
        except Exception as e:
            self.logger.error(f"Failed to get JSON: {str(e)}")
            return None

    def ensure_pinned(self, ipfs_hash: str) -> bool:
        """Ensure content remains pinned"""
        if not self.client:
            return False
            
        try:
            return self.client.pin.add(ipfs_hash)
        except Exception as e:
            self.logger.error(f"Failed to pin content: {str(e)}")
            return False