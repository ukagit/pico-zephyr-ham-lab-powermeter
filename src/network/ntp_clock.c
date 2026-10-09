#include <zephyr/kernel.h>
#include <zephyr/net/sntp.h>
#include <zephyr/logging/log.h>
#include "ntp_clock.h"
LOG_MODULE_REGISTER(hamlab_ntp, LOG_LEVEL_INF);
static K_MUTEX_DEFINE(clock_lock);
static bool synchronized;
static int64_t anchor_unix_ms, anchor_uptime_ms;
bool hamlab_ntp_now(int64_t *unix_ms)
{
    k_mutex_lock(&clock_lock,K_FOREVER);
    int64_t age=k_uptime_get()-anchor_uptime_ms;
    bool valid=synchronized&&age>=0&&age<86400000;
    if(valid)*unix_ms=anchor_unix_ms+age;
    k_mutex_unlock(&clock_lock);
    return valid;
}
static void ntp_thread(void *a,void *b,void *c)
{
    ARG_UNUSED(a);ARG_UNUSED(b);ARG_UNUSED(c);
    const char *servers[]={"pool.ntp.org","time.cloudflare.com"};
    unsigned server=0;
    for(;;) {
        struct sntp_time ts;
        int rc=sntp_simple(servers[server],5000,&ts);
        bool valid=!rc&&ts.seconds>=1577836800ULL&&ts.seconds<4102444800ULL;
        if(valid) {
            int64_t now=k_uptime_get();
            int64_t utc=(int64_t)ts.seconds*1000+((uint64_t)ts.fraction*1000>>32);
            k_mutex_lock(&clock_lock,K_FOREVER);
            anchor_unix_ms=utc;anchor_uptime_ms=now;synchronized=true;
            k_mutex_unlock(&clock_lock);
            LOG_INF("UTC synchronized via %s",servers[server]);
        } else LOG_DBG("NTP not available: %d",rc);
        server=(server+1)%2;
        /* Retry while WLAN/DNS starts; renew hourly. No meter lock held. */
        k_msleep(valid?3600000:30000);
    }
}
K_THREAD_DEFINE(ntp_id,2048,ntp_thread,NULL,NULL,NULL,10,0,10000);
