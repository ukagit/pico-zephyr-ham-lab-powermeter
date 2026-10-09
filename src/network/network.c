#include <errno.h>
#include <string.h>
#include <zephyr/kernel.h>
#include <zephyr/net/net_if.h>
#include <zephyr/net/net_mgmt.h>
#include <zephyr/net/wifi_mgmt.h>
#include <zephyr/net/dhcpv4.h>
#include <zephyr/net/dhcpv4_server.h>
#include <zephyr/shell/shell.h>
#include <zephyr/sys/atomic.h>
#include "network.h"
#define WIFI_CONNECT_TIMEOUT_MS 20000
#define WIFI_RETRY_MS 5000
#define AP_SSID "HamLab-DL2DBG"
#define AP_PASSWORD ""
#define AP_ADDRESS "192.168.4.1"
enum wifi_mode { MODE_STA, MODE_SWITCHING, MODE_AP, MODE_ERROR };
K_SEM_DEFINE(wifi_start_sem,0,1);
K_MUTEX_DEFINE(wifi_control_lock);
static atomic_t wifi_attempts=ATOMIC_INIT(0);
static atomic_t wifi_error=ATOMIC_INIT(0);
static atomic_t wifi_state=ATOMIC_INIT(0);
static atomic_t mode=ATOMIC_INIT(MODE_STA);
static bool ap_requested,ap_address_added;
static struct net_in_addr ap_addr;

int hamlab_network_start(void)
{
    if(net_if_get_first_wifi()==NULL)return -ENODEV;
    if(atomic_get(&mode)!=MODE_STA)return -EBUSY;
    k_sem_give(&wifi_start_sem);return 0;
}
static void wifi_thread(void *p1,void *p2,void *p3)
{
    ARG_UNUSED(p1);ARG_UNUSED(p2);ARG_UNUSED(p3);
    k_sem_take(&wifi_start_sem,K_FOREVER);
    while(true) {
        if(atomic_get(&mode)!=MODE_STA){k_msleep(200);continue;}
        struct net_if *iface=net_if_get_first_wifi();
        if(!iface){atomic_set(&wifi_state,4);atomic_set(&wifi_error,-ENODEV);k_msleep(WIFI_RETRY_MS);continue;}
        if(net_if_oper_state(iface)==NET_IF_OPER_UP){atomic_set(&wifi_state,2);atomic_set(&wifi_error,0);k_sleep(K_SECONDS(2));continue;}
        k_mutex_lock(&wifi_control_lock,K_FOREVER);
        if(atomic_get(&mode)!=MODE_STA){k_mutex_unlock(&wifi_control_lock);continue;}
        atomic_set(&wifi_state,1);atomic_inc(&wifi_attempts);
        int rc=net_mgmt(NET_REQUEST_WIFI_CONNECT_STORED,iface,NULL,0);
        if(rc)atomic_set(&wifi_error,rc);
        k_mutex_unlock(&wifi_control_lock);
        for(int waited=0;waited<WIFI_CONNECT_TIMEOUT_MS;waited+=500) {
            if(atomic_get(&mode)!=MODE_STA||net_if_oper_state(iface)==NET_IF_OPER_UP)break;
            k_msleep(500);
        }
        if(atomic_get(&mode)!=MODE_STA)continue;
        if(net_if_oper_state(iface)==NET_IF_OPER_UP)continue;
        if(!rc)atomic_set(&wifi_error,-ETIMEDOUT);
        atomic_set(&wifi_state,3);k_msleep(WIFI_RETRY_MS);
    }
}
K_THREAD_DEFINE(hamlab_wifi_id,2048,wifi_thread,NULL,NULL,NULL,11,0,0);

/* Caller holds control lock; never the measurement/display lock. */
static int ap_request(struct net_if *iface,bool enable,struct wifi_connect_req_params *params)
{
    /* AIROC completes AP start/stop synchronously and changes dormancy.
     * This driver emits no AP_ENABLE_RESULT / AP_DISABLE_RESULT events. */
    int rc;
    if(enable)rc=net_mgmt(NET_REQUEST_WIFI_AP_ENABLE,iface,params,sizeof(*params));
    else rc=net_mgmt(NET_REQUEST_WIFI_AP_DISABLE,iface,NULL,0);
    if(!rc) {
        if(enable)ap_requested=true;
        for(int i=0;i<50;i++) {
            bool up=net_if_oper_state(iface)==NET_IF_OPER_UP;
            if(up==enable)break;
            k_msleep(100);
        }
        if((net_if_oper_state(iface)==NET_IF_OPER_UP)!=enable)rc=-ETIMEDOUT;
    }
    if(!enable&&(rc==0||rc==-EALREADY||rc==-ENOTCONN)){ap_requested=false;rc=0;}
    return rc;
}
static void remove_ap_ip(struct net_if *iface)
{
    (void)net_dhcpv4_server_stop(iface);
    if(ap_address_added){net_if_ipv4_addr_rm(iface,&ap_addr);ap_address_added=false;}
}
static int start_ap_locked(const char *ssid,const char *password)
{
    size_t sl=strlen(ssid),pl=strlen(password);
    if(sl<1||sl>32||(pl!=0&&(pl<8||pl>63)))return -EINVAL;
    struct net_if *iface=net_if_get_first_wifi();if(!iface)return -ENODEV;
    if(atomic_get(&mode)!=MODE_STA)return -EBUSY;
    atomic_set(&mode,MODE_SWITCHING);atomic_set(&wifi_state,6);
    net_dhcpv4_stop(iface);
    int rc=net_mgmt(NET_REQUEST_WIFI_DISCONNECT,iface,NULL,0);
    if(rc&&rc!=-EALREADY&&rc!=-ENOTCONN)goto failed;
    for(int i=0;i<50&&net_if_oper_state(iface)==NET_IF_OPER_UP;i++)k_msleep(100);
    if(net_if_oper_state(iface)==NET_IF_OPER_UP){rc=-ETIMEDOUT;goto failed;}
    struct wifi_connect_req_params params={0};
    params.ssid=(const uint8_t *)ssid;params.ssid_length=sl;
    params.psk=pl?(const uint8_t *)password:NULL;params.psk_length=pl;
    params.channel=6;params.band=WIFI_FREQ_BAND_2_4_GHZ;
    params.security=pl?WIFI_SECURITY_TYPE_PSK:WIFI_SECURITY_TYPE_NONE;
    params.bandwidth=WIFI_FREQ_BANDWIDTH_20MHZ;
    rc=ap_request(iface,true,&params);if(rc)goto failed;
    struct net_in_addr mask,pool,gateway={0};
    net_addr_pton(NET_AF_INET,AP_ADDRESS,&ap_addr);
    net_addr_pton(NET_AF_INET,"255.255.255.0",&mask);
    net_addr_pton(NET_AF_INET,"192.168.4.10",&pool);
    if(!net_if_ipv4_addr_add(iface,&ap_addr,NET_ADDR_MANUAL,0)){rc=-ENOMEM;goto failed;}
    ap_address_added=true;
    if(!net_if_ipv4_set_netmask_by_addr(iface,&ap_addr,&mask)){rc=-EINVAL;goto failed;}
    net_if_ipv4_set_gw(iface,&gateway);
    rc=net_dhcpv4_server_start(iface,&pool);if(rc)goto failed;
    atomic_set(&mode,MODE_AP);atomic_set(&wifi_state,5);atomic_set(&wifi_error,0);
    return 0;
failed:
    remove_ap_ip(iface);
    if(ap_requested)(void)ap_request(iface,false,NULL);
    /* Explicit recovery avoids an unnoticed STA retry racing the AP test. */
    atomic_set(&mode,MODE_ERROR);atomic_set(&wifi_state,7);atomic_set(&wifi_error,rc);
    return rc;
}
int hamlab_network_boot(bool ap)
{
    if(!ap)return hamlab_network_start();
    k_mutex_lock(&wifi_control_lock,K_FOREVER);
    int rc=start_ap_locked(AP_SSID,AP_PASSWORD);
    k_mutex_unlock(&wifi_control_lock);
    return rc;
}
static int start_sta_locked(void)
{
    struct net_if *iface=net_if_get_first_wifi();if(!iface)return -ENODEV;
    if(atomic_get(&mode)==MODE_STA)return hamlab_network_start();
    atomic_set(&mode,MODE_SWITCHING);atomic_set(&wifi_state,6);
    if(ap_requested) {
        int rc=ap_request(iface,false,NULL);
        if(rc){atomic_set(&mode,MODE_ERROR);atomic_set(&wifi_state,7);atomic_set(&wifi_error,rc);return rc;}
    }
    remove_ap_ip(iface);
    atomic_set(&mode,MODE_STA);atomic_set(&wifi_state,0);atomic_set(&wifi_error,0);
    net_dhcpv4_start(iface);
    return hamlab_network_start();
}
static int cmd_wifi_stored(const struct shell *sh,size_t argc,char **argv)
{
    ARG_UNUSED(argc);ARG_UNUSED(argv);int rc=hamlab_network_start();
    if(rc)shell_error(sh,"Wi-Fi start: %d (use wifi_mode sta)",rc);
    else shell_print(sh,"Stored Wi-Fi connection requested");
    return rc;
}
static int cmd_network_status(const struct shell *sh,size_t argc,char **argv)
{
    ARG_UNUSED(argc);ARG_UNUSED(argv);
    const char *names[]={"idle","connecting","online","retry_wait","no_interface","ap_online","switching","mode_error"};
    const char *modes[]={"sta","switching","ap","error"};
    int state=atomic_get(&wifi_state),m=atomic_get(&mode);
    shell_print(sh,"wifi_mode: %s (RAM only; boot: GP21 pressed=AP, otherwise STA)",m>=0&&m<4?modes[m]:"unknown");
    shell_print(sh,"wifi_state: %s",state>=0&&state<8?names[state]:"unknown");
    shell_print(sh,"wifi_attempts: %ld",(long)atomic_get(&wifi_attempts));
    shell_print(sh,"wifi_error: %ld",(long)atomic_get(&wifi_error));
    if(m==MODE_AP)shell_print(sh,"AP: http://" AP_ADDRESS ":8080/; DHCP .10-.11; no Internet gateway");
    shell_print(sh,"TCP console: port 23; HTTP: port 8080");return 0;
}
static int cmd_wifi_mode(const struct shell *sh,size_t argc,char **argv)
{
    if(argc==1||(argc==2&&!strcmp(argv[1],"status")))return cmd_network_status(sh,argc,argv);
    bool ap=!strcmp(argv[1],"ap"),sta=!strcmp(argv[1],"sta");
    if((!ap&&!sta)||(sta&&argc!=2)||(ap&&argc!=2&&argc!=4)) {
        shell_error(sh,"wifi_mode ap [SSID PASSWORD] | sta | status");return -EINVAL;
    }
    if(k_mutex_lock(&wifi_control_lock,K_SECONDS(30))){shell_error(sh,"Wi-Fi control busy");return -EBUSY;}
    int rc=ap?start_ap_locked(argc==4?argv[2]:AP_SSID,argc==4?argv[3]:AP_PASSWORD):start_sta_locked();
    k_mutex_unlock(&wifi_control_lock);
    if(rc)shell_error(sh,"Wi-Fi switch failed: %d; use wifi_mode sta or reboot",rc);
    else if(ap)shell_print(sh,"AP ready: %s; %s; http://" AP_ADDRESS ":8080/",argc==4?argv[2]:AP_SSID,(argc==4&&argv[3][0])?"WPA2":"OPEN, no password");
    else shell_print(sh,"STA requested: reconnecting with saved credentials");
    return rc;
}
SHELL_CMD_REGISTER(wifi_stored,NULL,"Connect with saved Wi-Fi credentials",cmd_wifi_stored);
SHELL_CMD_REGISTER(network_status,NULL,"Show Wi-Fi connection state",cmd_network_status);
SHELL_CMD_REGISTER(wifi_mode,NULL,"RAM mode: ap [SSID PASSWORD] | sta | status; use USB",cmd_wifi_mode);
