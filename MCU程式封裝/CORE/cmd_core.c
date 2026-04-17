#include "cmd_core.h"
#include "cmd_core_internal.h"   // 包含 table + glue 宣告
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/* ----- 內部輔助函式 ----- */

/**
 * @brief tokenize payload，依空白分割
 * @param str 原始 payload
 * @param argv 儲存 token
 * @param max 最大 token 數量
 * @return token 個數
 */
static int tokenize(char* str, char** argv, int max)
{
    int count = 0;
    char* token = strtok(str, " ");
    while (token && count < max)
    {
        argv[count++] = token;
        token = strtok(NULL, " ");
    }
    return count;
}

/**
 * @brief 回傳錯誤訊息給 PC (你可改成 CDC_Printf)
 */
static void send_error(const char* msg)
{
    // TODO: 改成你專案的 CDC 或 log
    CDC_Printf("ERR:%s\r\n", msg);
}

/* ----- cmd_execute 實作 ----- */

bool cmd_execute(const char* payload)
{
    // 先複製字串，因 strtok 會修改
    char buf[128];
    if (strlen(payload) >= sizeof(buf))
    {
        send_error("TOO LONG");
        return false;
    }
    strcpy(buf, payload);

    char* argv[8];     // 最多支援 8 個 token
    int argc = tokenize(buf, argv, 8);
    if (argc == 0)
    {
        send_error("EMPTY CMD");
        return false;
    }

    const char* cmd_name = argv[0];
    int param_count = argc - 1;

    // 查表
    for (uint8_t i = 0; i < cmd_table_size; i++)
    {
        if (strcmp(cmd_table[i].name, cmd_name) == 0)
        {
            if (param_count != cmd_table[i].argc)
            {
                send_error("ARG");
                return false;
            }

            bool result = cmd_table[i].handler(param_count, &argv[1]);
            if (!result)
                send_error("HW FAIL");

            return result;
        }
    }

    send_error("UNKNOWN");
    return false;
}