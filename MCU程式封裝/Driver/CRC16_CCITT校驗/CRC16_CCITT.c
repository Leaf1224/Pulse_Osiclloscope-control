#include "crc16_ccitt.h"
#include <string.h>
#include <ctype.h>

#define CRC16_INIT 0xFFFF
#define CRC16_POLY 0x1021

/*--------------------------------------------------*/
/* Internal CRC16 calculator                        */
/*--------------------------------------------------*/
static uint16_t crc16_ccitt_calc(const uint8_t *data, uint16_t len)
{
    uint16_t crc = CRC16_INIT;

    for (uint16_t i = 0; i < len; i++)
    {
        crc ^= (uint16_t)data[i] << 8;

        for (uint8_t j = 0; j < 8; j++)
        {
            if (crc & 0x8000)
                crc = (crc << 1) ^ CRC16_POLY;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/*--------------------------------------------------*/
/* Public API                                       */
/*--------------------------------------------------*/
bool CRC16_CCITT_Check(const char *cmd)
{
    const char *star;
    uint16_t calc_crc;
    uint16_t recv_crc;

    /* Find '*' */
    star = strchr(cmd, '*');
    if (star == NULL)
        return false;

    /* Check CRC length (need 4 hex chars) */
    if (strlen(star + 1) < 4)
        return false;

    /* Parse received CRC */
    recv_crc = (uint16_t)strtol(star + 1, NULL, 16);

    /* Calculate CRC from '$' (excluded) to '*' (excluded) */
    if (cmd[0] != '$')
        return false;

    calc_crc = crc16_ccitt_calc(
        (const uint8_t *)(cmd + 1),
        (uint16_t)(star - cmd - 1)
    );

    return (calc_crc == recv_crc);
}
