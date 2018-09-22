from Crypto.Cipher import Salsa20

plaintext = b'asdf asdfasdf asdfa sdf'
secret = b'*Thirty-two byte (256 bits) key*'
cipher = Salsa20.new(key=secret)
msg = cipher.nonce + cipher.encrypt(plaintext)
print(plaintext)
print(msg)

secret = b'*Thirty-two byte (256 bits) key*'
msg_nonce = msg[:8]
ciphertext = msg[8:]
cipher = Salsa20.new(key=secret, nonce=msg_nonce)
result = cipher.decrypt(ciphertext)

print(result)


encryption_key = b'*Thirty-two byte (256 bits) key*'
token = b'1234'
print(token)
cipher = Salsa20.new(key=encryption_key)

msg = cipher.nonce + cipher.encrypt(token)
print(msg)
msg_nonce = msg[:8]
ciphertext = msg[8:]

cipher = Salsa20.new(key=encryption_key, nonce=msg_nonce)

plaintext = cipher.decrypt(ciphertext)
print(plaintext)
