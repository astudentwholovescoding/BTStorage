import magic
from toon_format import encode, decode
from hashlib import sha256


def generate_header(data_bytes, filename, description="", author="", nsfw_flag=False, license_type="Unknown", public=True, password=None, **kwargs):
    metadata_json = {
        "FileName": filename, # string
        "Description": description, # also a string
        "Author": author, # string
        "ContentType": magic.from_buffer(data_bytes, mime=True), # MIME type
        "ContentSize": len(data_bytes), # integer
        "FileHash": sha256(data_bytes).hexdigest(), # SHA256
        "NSFWFlag": nsfw_flag, # boolean
        "LicenseType": license_type, # type: "All Rights Reserved" | "CC0_1_0" | "CC_BY_4_0" | "CC_BY_SA_4_0" | "MIT" | "GPL_3_0" | "Proprietary" | "Unknown"
        "Public": public # boolean
    }

    if password is not None:
        metadata_json["Locked"] = True
        metadata_json["PasswordHash"] = sha256(sha256(password.encode()).hexdigest().encode()).hexdigest()
    else:
        metadata_json["Locked"] = False
    
    for kwarg in kwargs.items():
        metadata_json[kwarg[0]] = kwarg[1]

    metadata_toon = encode(dict(sorted(metadata_json.items())))

    header = f"{len(metadata_toon)}\n{metadata_toon}"

    return header

def get_header_size(data):
    header_length_str = data.split('\n')[0]

    header_size = len(header_length_str) + int(header_length_str) + 2 # \n

    return header_size

def parse_header(data):
    header_size = get_header_size(data)

    header_str = data[data.find('\n'):header_size]

    header = decode(header_str)

    return header