import struct
from typing import Tuple

from ledgercomm import Transport

from archethic_client.archethic_cmd_builder import ArchethicCommandBuilder, InsType
import requests
from archethic_client.exception import DeviceException
from archethic_client.transaction import Transaction


class ArchethicCommand:
    def __init__(self,
                 transport: Transport,
                 debug: bool = False) -> None:
        self.transport = transport
        self.builder = ArchethicCommandBuilder(debug=debug)
        self.debug = debug

    def get_app_and_version(self) -> Tuple[str, str]:
        sw, response = self.transport.exchange_raw(
            self.builder.get_app_and_version()
        )  # type: int, bytes

        if sw != 0x9000:
            raise DeviceException(error_code=sw, ins=0x01)

        # response = format_id (1) ||
        #            app_name_len (1) ||
        #            app_name (var) ||
        #            version_len (1) ||
        #            version (var) ||
        offset: int = 0

        format_id: int = response[offset]
        offset += 1
        app_name_len: int = response[offset]
        offset += 1
        app_name: str = response[offset:offset + app_name_len].decode("ascii")
        offset += app_name_len
        version_len: int = response[offset]
        offset += 1
        version: str = response[offset:offset + version_len].decode("ascii")
        offset += version_len

        return app_name, version

    def get_version(self) -> Tuple[int, int, int]:
        sw, response = self.transport.exchange_raw(
            self.builder.get_version()
        )  # type: int, bytes

        print(sw, response)

        if sw != 0x9000:
            raise DeviceException(error_code=sw, ins=InsType.INS_GET_VERSION)

        # response = MAJOR (1) || MINOR (1) || PATCH (1)
        assert len(response) == 3

        major, minor, patch = struct.unpack(
            "BBB",
            response
        )  # type: int, int, int

        return major, minor, patch

    def get_public_key(self, hid, display: bool = False) -> Tuple[hex, hex, hex, hex, hex]:
        self.transport.send_raw(
            self.builder.get_public_key(display=display)
        )  # type: int, bytes

        if (not hid):
            button = "http://127.0.0.1:5000/button/"
            url = button + "right"
            payload = '{"action":"press-and-release"}'
            for _ in range(10):
                res = requests.post(url, data=payload)
            url = button + "both"
            res = requests.post(url, data=payload)

        sw, response = self.transport.recv()
        if sw != 0x9000:
            raise DeviceException(error_code=sw, ins=InsType.INS_GET_PUBLIC_KEY)

        response = response.hex()

        # print (response)
        # print(len(response))

        offset: int = 0

        curve_type: hex = response[offset: offset + 2]
        offset += 2
        device_origin: hex = response[offset:offset + 2]
        offset += 2
        path_form: hex = response[offset:offset + 2]
        offset += 2
        x: hex = response[offset:offset + 64]
        offset += 64
        y: hex = response[offset:offset + 64]

        # curve_type => 0: ED25519, 1: NISTP256, 2: SECP256K1
        # device_origin => 0 -> Onchain Wallet , 1 -> Software wallet , 2 -> TPM(Node) , 3 -> Yubikey(Node, hardware Wallet) , 4 -> Ledger (Hardware Wallet)
        # path_form => 04 means uncompressed form
        # x => x on curve path uncompressed form
        # y => y on curve path uncompressed form

        assert len(response) == 134  # 1 bytes + 1 bytes + 1 byte + 32 bytes + 32 bytes

        return curve_type, device_origin, path_form, x, y

    def get_arch_addr(self, hid, enc_oc_wallet, service_index, display: bool = False):
        self.transport.send_raw(
            self.builder.get_arch_address(enc_oc_wallet, service_index, display=display,)
        )  # type: int, bytes

        if (not hid):
            button = "http://127.0.0.1:5000/button/"
            url = button + "right"
            payload = '{"action":"press-and-release"}'
            for _ in range(6):
                res = requests.post(url, data=payload)
            url = button + "both"
            res = requests.post(url, data=payload)

        sw, response = self.transport.recv()

        if sw != 0x9000:
            raise DeviceException(error_code=sw, ins=InsType.INS_GET_PUBLIC_KEY)

        response = response.hex()

        offset: int = 0
        curve_type: hex = response[offset: offset + 2]
        offset += 2
        hash_type: hex = response[offset: offset + 2]
        offset += 2
        hash_enc_pub_key = response[offset:]

        # curve_type => 0: ED25519, 1: NISTP256, 2: SECP256K1
        # hash_type => 0 -> SHA256 (sha2) 1 -> SHA512 (sha2) 2 -> SHA3_256 (keccak) 3 -> SHA3_512 (keccak) 4 -> BLAKE2B
        # hash_enc_pub_key => According to hash type hashed encoded public key

        return curve_type, hash_type, hash_enc_pub_key

    def sign_txn_hash(self, hid, enc_oc_wallet, service_index, receiver_addr, amount, display: bool = False):

        self.transport.send_raw(
            self.builder.sign_txn_hash_build(
                enc_oc_wallet, service_index, receiver_addr, amount, display)
        )  # type: int, bytes

        if (not hid):
            button = "http://127.0.0.1:5000/button/"
            url = button + "right"
            payload = '{"action":"press-and-release"}'
            for _ in range(7):
                res = requests.post(url, data=payload)

            url = button + "both"
            res = requests.post(url, data=payload)

        sw, response = self.transport.recv()
        if sw != 0x9000:
            raise DeviceException(error_code=sw, ins=InsType.INS_GET_PUBLIC_KEY)

        response = response.hex()

        #  APDU Response have following
        # Final Tx Hash (SHA256) || Corresponding public key from whose private key the signature was made ||  ASN DER Signature ||

        print("len res: ", len(response))

        offset = 0
        final_txn_hash = response[offset: offset + 64]
        print(final_txn_hash)

        offset += 64

        curve_type = response[offset: offset + 2]
        origin_type = response[offset + 2: offset + 4]
        pubkey_tag = response[offset + 4: offset + 6]
        # Check for the form 04 mean it is uncompressed
        assert(pubkey_tag == "04")
        public_key = response[offset:offset+67*2]
        print(public_key)
        offset += 67*2

        print("Offset After Extracting PublicKey: ", offset)
        sign_tag: hex = response[offset: offset + 2]
        # Check if sign tag
        assert(sign_tag == "30")
        sign_len = response[offset + 2: offset + 4]
        asn_der_sign = response[offset: offset + 4 + (int(sign_len, base=16)*2)]
        offset += (int(sign_len, base=16)*2) + 4

        return final_txn_hash, curve_type, origin_type, pubkey_tag, public_key, sign_tag, sign_len, asn_der_sign

    def sign_txn_hash_origin(self, hid, txnHashLen, txnHash, display: bool = False):
        self.transport.send_raw(
            self.builder.sign_txn_hash_origin_build(
                txnHashLen, txnHash, display)
        )  # type: int, bytes

        if (not hid):
            button = "http://127.0.0.1:5000/button/"
            url = button + "right"
            payload = '{"action":"press-and-release"}'
            for _ in range(6):
                res = requests.post(url, data=payload)

            url = button + "both"
            res = requests.post(url, data=payload)

        sw, response = self.transport.recv()
        if sw != 0x9000:
            raise DeviceException(error_code=sw, ins=InsType.INS_GET_PUBLIC_KEY)

        response = response.hex()

        #  APDU Response have following
        # Final Tx Hash (SHA256) || Corresponding public key from whose private key the signature was made ||  ASN DER Signature ||

        print("len res: ", len(response))

        offset = 0

        curve_type = response[offset: offset + 2]
        origin_type = response[offset + 2: offset + 4]
        pubkey_tag = response[offset + 4: offset + 6]
        # Check for the form 04 mean it is uncompressed
        assert(pubkey_tag == "04")
        public_key = response[offset:offset+67*2]
        print(public_key)
        offset += 67*2

        print("Offset After Extracting PublicKey: ", offset)
        sign_tag: hex = response[offset: offset + 2]
        # Check if sign tag
        assert(sign_tag == "30")
        sign_len = response[offset + 2: offset + 4]
        asn_der_sign = response[offset: offset + 4 + (int(sign_len, base=16)*2)]
        offset += (int(sign_len, base=16)*2) + 4

        return curve_type, origin_type, pubkey_tag, public_key, sign_tag, sign_len, asn_der_sign
