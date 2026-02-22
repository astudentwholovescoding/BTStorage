import os
import json
import time
import base64
import requests
from bit import PrivateKeyTestnet

from .chunking import chunk_text, base64_encode
from .metadata import generate_header, parse_header, get_header_size
from .encryption import encode_data


class BTStorage:
    def __init__(self, db_path='db.json'):
        self.db_path = db_path

        if os.path.exists(db_path):
            with open(db_path) as db_file:
                json_data = json.load(db_file)

                self.main_key = PrivateKeyTestnet(json_data['main_wif'])
                self.keys = []
                for wif in json_data['files_wifs']:
                    self.keys.append(PrivateKeyTestnet(wif))

        else:
            self.main_key = PrivateKeyTestnet()
            self.keys = []
    
    def get_main_address(self):
        return self.main_key.segwit_address
    
    def get_balance(self, key):
        balance = None
        while balance is None:
            try:
                balance = key.get_balance()
            except Exception:
                time.sleep(10)
        return int(balance)
    
    def get_main_balance(self):
        return self.get_balance(self.main_key)

    def refund(self):
        temp_key = PrivateKeyTestnet()
        print(temp_key.segwit_address)
        while self.get_balance(temp_key) == 0:
            time.sleep(10)
        temp_tx = self.create_tx(temp_key, [], leftover=self.get_main_address())
        self.push_tx(temp_tx)
    
    def save(self):
        with open(self.db_path, 'w') as db_file:
            json.dump(
                {
                    "main_wif": self.main_key.to_wif(),
                    "files_wifs": [
                        key.to_wif() for key in self.keys
                    ]
                }, db_file, indent=2
            )
    
    def create_tx(self, key, *args, **kwargs):
        tx_generated = False
        while not tx_generated:
            try:
                tx_hex = key.create_transaction(*args, **kwargs)
                tx_generated = True
            except Exception:
                time.sleep(10)
        return tx_hex

    def push_tx(self, tx_hex):
        headers = {'Content-Type': 'application/json'}
        json_data = {'raw_tx': tx_hex}
        
        pushed = False
        while not pushed:
            response = requests.post('https://mempush.com/testnetv3/api/transaction/push', headers=headers, json=json_data)
            pushed = response.status_code == 201
            if not pushed:
                time.sleep(60)
        return response.json()['txid']
    
    def upload_file(self, file_path, file_name, password=None, **kwargs):
        new_key = PrivateKeyTestnet()
        new_key_address = new_key.segwit_address
        self.keys.append(new_key)

        with open(file_path, 'rb') as file:
            file_data = file.read()

            if password is not None:
                file_data = encode_data(file_data, password)

            data = f"{generate_header(file_data, file_name, password=password, **kwargs)}\n{base64_encode(file_data)}"
        
        chunks = chunk_text(data)

        for i, chunk in enumerate(chunks):
            tx_hex = self.create_tx(
                self.main_key,
                [(new_key_address, 550 + i, 'satoshi')],
                message=chunk
            )

            print(i, self.push_tx(tx_hex))

            if i % 20 == 0 and i != 0:
                back_tx_hex = self.create_tx(new_key, [], leftover=self.get_main_address())
                self.push_tx(back_tx_hex)
        
        time.sleep(60 * 5)

        key_txs = requests.get(f"https://mempool.space/testnet/api/address/{new_key_address}/txs").json()

        valid_txs = []
        for tx in key_txs:
            for vout in tx['vout']:
                if vout.get('scriptpubkey_address') == new_key_address and vout.get('scriptpubkey_type') == 'p2sh':
                    valid_txs.append(vout['value'] - 550)
        
        while len(valid_txs) != len(chunks):
            for i, chunk in enumerate(chunks):
                if i not in valid_txs:
                    tx_hex = self.create_tx(
                        self.main_key,
                        [(new_key_address, 550 + i, 'satoshi')],
                        message=chunk
                    )

                    print(i, self.push_tx(tx_hex))

            time.sleep(5)
            key_txs = requests.get(f"https://mempool.space/testnet/api/address/{new_key_address}/txs").json()

            valid_txs = []
            for tx in key_txs:
                for vout in tx['vout']:
                    if vout.get('scriptpubkey_address') == new_key_address and vout.get('scriptpubkey_type') == 'p2sh':
                        valid_txs.append(vout['value'] - 550)

        back_tx_hex = self.create_tx(new_key, [], leftover=self.get_main_address())
        self.push_tx(back_tx_hex)

        return new_key_address
    
    def list_files(self):
        files = []

        for key in self.keys:
            key_address = key.segwit_address
            
            header = self.get_file_header(key_address)

            files.append(header)

        return files
    
    def get_file(self, file_address):
        file_txs = requests.get(f"https://mempool.space/testnet/api/address/{file_address}/txs").json()

        chunks = []
        for tx in file_txs:
            chunk_data = None
            for vout in tx['vout']:
                if vout.get('scriptpubkey_address') == file_address and vout.get('scriptpubkey_type') == "p2sh":
                    chunk_idx = vout['value']
                elif vout.get('scriptpubkey_type') == "op_return":
                    chunk_data = vout['scriptpubkey_asm'].split(' ')[-1]
            if chunk_data is not None:
                chunks.append(
                    {
                        "index": chunk_idx,
                        "data": bytes.fromhex(chunk_data).decode()
                    }
                )
        
        chunks.sort(key=lambda block: block.get('index'))
        data = ''.join(chunk['data'] for chunk in chunks)
    
        return data
    
    def get_file_header(self, file_address):
        data = self.get_file(file_address)
        header = parse_header(data)
        return header
    
    def get_file_content(self, file_address):
        file_data = self.get_file(file_address)

        header = parse_header(file_data)
        
        file_content_b64 = file_data[get_header_size(file_data):]
        file_content = base64.b64decode(file_content_b64.encode())

        return file_content