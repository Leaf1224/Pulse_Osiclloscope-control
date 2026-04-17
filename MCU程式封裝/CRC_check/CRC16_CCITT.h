#ifndef CRC16_CCITT_H
#define CRC16_CCITT_H

#include <stdint.h>
#include <stdbool.h>

/**
 * @brief Check CRC16-CCITT of command string
 * @param cmd  Command string, format:
 *             "$DATA*XXXX"
 * @return true  CRC correct
 * @return false CRC error or format error
 */
bool CRC16_CCITT_Check(const char *cmd);
#endif
