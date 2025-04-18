import ipfshttpclient
import json

class IPFSHandler:
    def __init__(self):
        try:
            # Connect to local IPFS daemon
            self.client = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
        except:
            self.client = None
            print("Failed to connect to IPFS. Make sure IPFS daemon is running.")
    
    def add_file(self, file_path):
        """Add a file to IPFS and return its hash"""
        if not self.client:
            return None
        
        res = self.client.add(file_path)
        return res['Hash']
    
    def add_json(self, data):
        """Add JSON data to IPFS and return its hash"""
        if not self.client:
            return None
        
        json_str = json.dumps(data)
        res = self.client.add_json(json_str)
        return res
    
    def get_json(self, ipfs_hash):
        """Get JSON data from IPFS using its hash"""
        if not self.client:
            return None
        
        data = self.client.get_json(ipfs_hash)
        return data
    
    def pin_hash(self, ipfs_hash):
        """Pin a hash to keep it in IPFS storage"""
        if not self.client:
            return None
        
        return self.client.pin.add(ipfs_hash)