#ifndef HAMLAB_NTP_CLOCK_H
#define HAMLAB_NTP_CLOCK_H
#include <stdbool.h>
#include <stdint.h>
/* UTC Unix milliseconds. False before sync or after 24 h without sync. */
bool hamlab_ntp_now(int64_t *unix_ms);
#endif
