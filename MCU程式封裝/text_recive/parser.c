#include "parser.h"
#include <stdbool.h>
#include <stdint.h>

#define RING_BUF_SIZE 512   // buffer大小可依需求調整
#define PARSER_MAX_PACKET 128 //解析後指令buffer最大容量
/* ================= ring buffer ================= */

static uint8_t rb[RING_BUF_SIZE];   //  創建buffer
static volatile uint16_t rb_head = 0;   //  寫入指針
static volatile uint16_t rb_tail = 0;   //  讀取指針

/* ================= parser buffer ================= */

static enum {
    WAIT_START,
    IN_PACKET
} state;
static char packet[PARSER_MAX_PACKET];//解析後存指令的buffer
static uint16_t pkt_idx;//解析完成存指令的buffer(packet)的指針

/* ================= internal helpers ================= */

static inline uint16_t rb_next(uint16_t idx)//計算下一個head或Tail在哪
{
    return (uint16_t)((idx + 1) % RING_BUF_SIZE);
}

/* ================= public API ================= */

/**
 * @brief  將 CDC_Receive_FS 收到的 raw bytes 丟進 ring buffer
 * @note   可在 USB 中斷中呼叫
 */
void Parser_PushBytes(uint8_t *buf, uint32_t len)
{
    for (uint32_t i = 0; i < len; i++)
    {
        uint16_t next = rb_next(rb_head);

        if (next != rb_tail)     // buffer 尚未滿
        {
            rb[rb_head] = buf[i];
            rb_head = next;
        }
        else
        {
            //如果Buffer滿了就會跑到這邊(要寫入的地方還未被解析到)
            // buffer 滿了：資料丟棄（可加 error counter）
            // overflow_count++;
        }
    }
}


void parser_init(void)
{
    rb_head = rb_tail = 0;
    pkt_idx = 0;
    state = WAIT_START;
}

bool parser_poll(void)//輪尋找完整指令，找到會回True
{
    while (rb_tail != rb_head)
    {
        uint8_t ch = rb[rb_tail];
        rb_tail = (rb_tail + 1) % sizeof(rb);//更新Tail，如Tail為尾則從0開始(其實跟上面的internal helpers是一樣東西)

        switch (state)
        {
        case WAIT_START:
            if (ch == '$')
            {
                pkt_idx = 0;
                packet[pkt_idx++] = ch;
                state = IN_PACKET;
            }
            break;

        case IN_PACKET:
            packet[pkt_idx++] = ch;//塞字進packet
            if (pkt_idx >= PARSER_MAX_PACKET)//存指令的buffer爆了
            {
                state = WAIT_START;
                pkt_idx = 0;
            }
            else if (ch == '\n')//找到結尾字符了
            {
                packet[pkt_idx] = '\0';
                state = WAIT_START;
                return true;   // packet內存好完整指令
            }
            break;
        }
    }
    return false;
}

const char* parser_get_packet(void)//將packet內存好完整指令丟進Main
{
    return packet;
}