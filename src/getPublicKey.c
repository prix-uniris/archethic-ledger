// elixir verify
// public_key = Base.decode16!("", case: :lower)
// sign = Base.decode16!("", case: :lower)
// :crypto.verify(:ecdsa, :sha256, "archethic", sign, [public_key, :secp256k1])

#include <stdint.h>
#include <stdbool.h>
#include <os.h>
#include <os_io_seproxyhal.h>
#include <cx.h>
#include "archethic.h"

typedef void (*action_validate_cb)(bool);

static action_validate_cb g_validate_callback;
// 1 + 4 + 130
static char g_public_key[135];

static char g_bip44_path[60];
cx_ecfp_public_key_t publicKey;

// Step with icon and text
UX_STEP_NOCB(ux_display_confirm_addr_step, bnnn_paging, {
                                                            .title = "Confirm Origin",
                                                            .text = "Public Key",
                                                        });
// Step with title/text for BIP32 path
UX_STEP_NOCB(ux_display_path_step,
             bnnn_paging,
             {
                 .title = "bip44 Path",
                 .text = g_bip44_path,
             });
// Step with title/text for public key
UX_STEP_NOCB(ux_display_public_key_step,
             bnnn_paging,
             {
                 .title = "Public Key",
                 .text = g_public_key,
             });
// Step with approve button
UX_STEP_CB(ux_display_approve_step,
           pb,
           (*g_validate_callback)(true),
           {
               &C_icon_validate_14,
               "Approve",
           });
// Step with reject button
UX_STEP_CB(ux_display_reject_step,
           pb,
           (*g_validate_callback)(false),
           {
               &C_icon_crossmark,
               "Reject",
           });

// FLOW to display public key and BIP44 path:
// #1 screen: "confirm public key" text
// #2 screen: display BIP44 Path
// #3 screen: display public key
// #4 screen: approve button
// #5 screen: reject button
UX_FLOW(ux_display_pubkey_flow,
        &ux_display_confirm_addr_step,
        &ux_display_path_step,
        &ux_display_public_key_step,
        &ux_display_approve_step,
        &ux_display_reject_step);

void ui_action_validate_pubkey(bool choice)
{

    if (choice)
    {
        G_io_apdu_buffer[0] = 2;
        // Ledger Origin Device
        G_io_apdu_buffer[1] = 4;
        for (int v = 0; v < (int)publicKey.W_len; v++)
            G_io_apdu_buffer[v + 2] = publicKey.W[v];

        io_exchange_with_code(SW_OK, publicKey.W_len + 2);
    }
    else
    {
        io_exchange_with_code(SW_USER_REJECTED, 0);
    }

    ui_menu_main();
}

int ui_display_public_key()
{

    memset(g_bip44_path, 0, sizeof(g_bip44_path));
    memset(g_public_key, 0, sizeof(g_public_key));

    getOriginPublicKey(&publicKey);
    snprintf(g_public_key, sizeof(g_public_key), "0204%.*H", publicKey.W_len, publicKey.W);

    // g_bip44_path = "m/44'/650'/ffff'/0'/0'" always
    strncpy(g_bip44_path, "m/44'/650'/ffff'/0'/0'", 60);

    g_validate_callback = &ui_action_validate_pubkey;
    ux_flow_init(0, ux_display_pubkey_flow, NULL);

    return 0;
}

void handleGetPublicKey(uint8_t p1, uint8_t p2, uint8_t *dataBuffer, uint16_t dataLength, volatile unsigned int *flags, volatile unsigned int *tx)
{
    ui_display_public_key();
    *flags |= IO_ASYNCH_REPLY;
}
