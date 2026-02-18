import base64


def base64_encode(data):
    b64_data = base64.b64encode(data)
    b64_str = b64_data.decode()
    return b64_str 

def chunk_text(data, chunk_size=40):
    chunks = []
    for i in range(len(data) // chunk_size):
        chunks.append(data[i * chunk_size: (i+1) * chunk_size])
    if len(data) % chunk_size != 0:
        chunks.append(data[0 - (len(data) % chunk_size):])
    return chunks

def base64_chunk(data):
    b64_data = base64.b64encode(data)
    b64_str = b64_data.decode()
    return chunk_text(b64_str)


chunk_functions = {
    "text": chunk_text,
    "bytes": base64_chunk
}

def chunk_data(data, datatype):
    return chunk_functions[datatype](data)
