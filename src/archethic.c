// uint8_t masterSeed[] = {0x9A, 0x34, 0xA2, 0x33, 0xC4, 0x8B, 0x77, 0xD4, 0x88, 0x56, 0xED, 0x17, 0x17, 0x92, 0xD0, 0xB1, 0x67, 0xF5, 0x0D, 0x9A, 0x81, 0x48, 0x76, 0x9E, 0x00, 0x0D, 0x1F, 0x3C, 0x75, 0xF7, 0x4C, 0x15};
#include "archethic.h"

void deriveArchEthicKeyPair(uint32_t keyIndex, cx_ecfp_private_key_t *privateKey, cx_ecfp_public_key_t *publicKey)
{
    uint8_t keySeed[32];
    cx_ecfp_private_key_t walletPrivateKey;

    // bip32 path for 44'/650'/n'/0'/0'
    uint32_t bip32Path[] = {44 | 0x80000000, 650 | 0x80000000, keyIndex | 0x80000000, 0x80000000, 0x80000000};

    // Derive the seed for given path
    os_perso_derive_node_bip32(CX_CURVE_256K1, bip32Path, 5, keySeed, NULL);

    // Initiate the private key with the seed
    cx_ecfp_init_private_key(CX_CURVE_256K1, keySeed, 32, &walletPrivateKey);

    if (publicKey)
    {
        // Derive the corresponding public key
        cx_ecfp_init_public_key(CX_CURVE_256K1, NULL, 0, publicKey);
        cx_ecfp_generate_pair(CX_CURVE_256K1, publicKey, &walletPrivateKey, 1);
    }
    if (privateKey)
    {
        *privateKey = walletPrivateKey;
    }
    explicit_bzero(keySeed, sizeof(keySeed));
    explicit_bzero(&walletPrivateKey, sizeof(walletPrivateKey));
}
