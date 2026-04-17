#ifndef PARSER_H
#define PARSER_H

#include <stdint.h>
#include <stdbool.h>
void parser_init(void);
void Parser_PushBytes(uint8_t *buf, uint32_t len);//將接收到的字串丟進ring Buffer，使用時放在usbd_cdc_if.c的CDC_Receive_FS內
bool parser_poll(void);/* main loop 輪巡呼叫：解析資料(找開頭結尾字符) */
const char* parser_get_CRC_packet(void);/* main loop 呼叫：回傳找到的指令給CRC校驗*/
const char* parser_get_CMD_payload(void);/* main loop 呼叫：回傳找到的指令給core執行指令*/

#endif
