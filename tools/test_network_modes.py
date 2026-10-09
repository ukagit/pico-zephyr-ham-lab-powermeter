"""Compile actual network.c against mocks and check AP/STA outcomes; no hardware."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parent.parent
HEADER=r'''
#ifndef MOCK_NETWORK_API_H
#define MOCK_NETWORK_API_H
#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stdio.h>
#include <errno.h>
#include <assert.h>
#include <arpa/inet.h>
#define ARG_UNUSED(x) (void)(x)
#define K_FOREVER (-1)
#define K_SECONDS(x) ((x)*1000)
typedef int atomic_t;
#define ATOMIC_INIT(x) (x)
static inline int atomic_get(atomic_t *p){return *p;}
static inline void atomic_set(atomic_t *p,int x){*p=x;}
static inline void atomic_inc(atomic_t *p){++*p;}
struct k_sem {int count;};
#define K_SEM_DEFINE(n,c,max) static struct k_sem n={c}
#define K_MUTEX_DEFINE(n) static int n
static inline void k_sem_give(struct k_sem *s){s->count=1;}
static inline void k_sem_reset(struct k_sem *s){s->count=0;}
static inline int k_sem_take(struct k_sem *s,int t){if(s->count){s->count=0;return 0;}return -1;}
static inline int k_mutex_lock(int *m,int t){return 0;}
static inline void k_mutex_unlock(int *m){}
static inline void k_msleep(int t){}
static inline void k_sleep(int t){}
#define K_THREAD_DEFINE(n,s,f,a,b,c,p,o,d) static void *n __attribute__((unused))=(void *)&f
struct net_if {int up;};
struct net_in_addr {uint32_t s_addr;};
#define NET_IF_OPER_UP 1
#define NET_AF_INET AF_INET
#define NET_ADDR_MANUAL 1
#define NET_EVENT_WIFI_AP_ENABLE_RESULT 1
#define NET_EVENT_WIFI_AP_DISABLE_RESULT 2
#define NET_REQUEST_WIFI_CONNECT_STORED 3
#define NET_REQUEST_WIFI_DISCONNECT 4
#define NET_REQUEST_WIFI_AP_ENABLE 5
#define NET_REQUEST_WIFI_AP_DISABLE 6
#define WIFI_FREQ_BAND_2_4_GHZ 0
#define WIFI_SECURITY_TYPE_NONE 0
#define WIFI_SECURITY_TYPE_PSK 1
#define WIFI_FREQ_BANDWIDTH_20MHZ 1
struct wifi_connect_req_params {const uint8_t *ssid,*psk;size_t ssid_length,psk_length;int channel,band,security,bandwidth;};
struct net_mgmt_event_callback {void *info;size_t info_length;void (*handler)(struct net_mgmt_event_callback *,uint64_t,struct net_if *);};
struct shell {int dummy;};
#define SHELL_CMD_REGISTER(n,x,h,f) static void *n##_registered __attribute__((unused))=(void *)&f
static inline void shell_print(const struct shell *s,const char *f,...){}
static inline void shell_error(const struct shell *s,const char *f,...){}
static struct net_if fake_iface;

static int request_error,dhcp_error,disable_error,silent_enable;
static int dhcp_running,client_starts,ip_present,disconnects,ap_starts,ap_stops;
static inline struct net_if *net_if_get_first_wifi(void){return &fake_iface;}
static inline int net_if_oper_state(struct net_if *i){return i->up;}
static inline void net_mgmt_init_event_callback(struct net_mgmt_event_callback *c,void (*f)(struct net_mgmt_event_callback *,uint64_t,struct net_if *),uint64_t m){c->handler=f;}
static inline void net_mgmt_add_event_callback(struct net_mgmt_event_callback *c){}
static inline int net_addr_pton(int f,const char *s,void *a){return inet_pton(f,s,a);}
static inline void net_dhcpv4_stop(struct net_if *i){}
static inline void net_dhcpv4_start(struct net_if *i){client_starts++;}
static inline int net_dhcpv4_server_start(struct net_if *i,struct net_in_addr *a){if(ntohl(a->s_addr)!=0xc0a8040a)return -EINVAL;if(!dhcp_error)dhcp_running=1;return dhcp_error;}
static inline int net_dhcpv4_server_stop(struct net_if *i){dhcp_running=0;return 0;}
static inline void *net_if_ipv4_addr_add(struct net_if *i,struct net_in_addr *a,int type,int life){ip_present=1;return i;}
static inline bool net_if_ipv4_addr_rm(struct net_if *i,struct net_in_addr *a){ip_present=0;return true;}
static inline bool net_if_ipv4_set_netmask_by_addr(struct net_if *i,struct net_in_addr *a,struct net_in_addr *m){return ntohl(m->s_addr)==0xffffff00;}
static inline void net_if_ipv4_set_gw(struct net_if *i,struct net_in_addr *a){}
static inline int mock_net_mgmt(int req,struct net_if *i,void *p,size_t len){
 if(req==NET_REQUEST_WIFI_DISCONNECT){disconnects++;i->up=0;return 0;}
 if(req==NET_REQUEST_WIFI_AP_ENABLE){ap_starts++;if(request_error)return request_error;struct wifi_connect_req_params *v=p;assert(v->bandwidth==WIFI_FREQ_BANDWIDTH_20MHZ);assert(v->security==(v->psk_length?WIFI_SECURITY_TYPE_PSK:WIFI_SECURITY_TYPE_NONE));if(!v->psk_length)assert(v->psk==NULL);if(!silent_enable)i->up=1;}
 if(req==NET_REQUEST_WIFI_AP_DISABLE){ap_stops++;if(disable_error)return disable_error;i->up=0;}
 return 0;
}
/* Mirror Zephyr token-pasting instead of hiding it behind an ordinary function. */
#define net_mgmt_NET_REQUEST_WIFI_CONNECT_STORED mock_net_mgmt
#define net_mgmt_NET_REQUEST_WIFI_DISCONNECT mock_net_mgmt
#define net_mgmt_NET_REQUEST_WIFI_AP_ENABLE mock_net_mgmt
#define net_mgmt_NET_REQUEST_WIFI_AP_DISABLE mock_net_mgmt
#define net_mgmt(request, iface, data, len) net_mgmt_##request(request, iface, data, len)
#endif
'''
HARNESS=r'''
#include <assert.h>
#include "network.c"
static void reset(void){
 fake_iface.up=1;request_error=dhcp_error=disable_error=silent_enable=0;
 dhcp_running=client_starts=ip_present=disconnects=ap_starts=ap_stops=0;
 ap_requested=ap_address_added=false;mode=MODE_STA;wifi_state=2;
}
int main(void){
 reset();assert(hamlab_network_boot(true)==0);assert(mode==MODE_AP&&dhcp_running&&disconnects==1);
 assert(start_sta_locked()==0);
 reset();assert(hamlab_network_boot(false)==0);assert(mode==MODE_STA&&ap_starts==0&&wifi_start_sem.count==1);
 reset();assert(start_ap_locked("HamLab","short")==-EINVAL);assert(disconnects==0&&mode==MODE_STA);
 reset();assert(start_ap_locked("HamLab","test12345")==0);assert(mode==MODE_AP&&dhcp_running&&ip_present);
 assert(hamlab_network_start()==-EBUSY);assert(ntohl(ap_addr.s_addr)==0xc0a80401);
 assert(start_sta_locked()==0);assert(mode==MODE_STA&&!dhcp_running&&!ip_present&&client_starts==1&&ap_stops==1);
 reset();request_error=-ENOTSUP;assert(start_ap_locked("HamLab","test12345")==-ENOTSUP);assert(mode==MODE_ERROR&&!dhcp_running&&!ip_present);assert(hamlab_network_start()==-EBUSY);assert(start_sta_locked()==0&&mode==MODE_STA);
 reset();dhcp_error=-ENOMEM;assert(start_ap_locked("HamLab","test12345")==-ENOMEM);assert(mode==MODE_ERROR&&!ip_present&&!dhcp_running&&ap_stops==1);
 reset();silent_enable=1;assert(start_ap_locked("HamLab","test12345")==-ETIMEDOUT);assert(mode==MODE_ERROR&&ap_stops==1);
 reset();assert(start_ap_locked("HamLab","test12345")==0);disable_error=-EIO;assert(start_sta_locked()==-EIO);assert(mode==MODE_ERROR&&ap_requested&&dhcp_running);disable_error=0;assert(start_sta_locked()==0&&!dhcp_running);
 puts("AP/STA mock checks passed: synchronous success without events, validation, interface timeout, radio/DHCP failures and recovery.");
 return 0;
}
'''
class NetworkModesTest(unittest.TestCase):
    def test_real_network_code(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'mock.h').write_text(HEADER)
            for name in ('kernel.h','net/net_if.h','net/net_mgmt.h','net/wifi_mgmt.h','net/dhcpv4.h','net/dhcpv4_server.h','shell/shell.h','sys/atomic.h'):
                p=d/'zephyr'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('#include "mock.h"\n')
            (d/'test.c').write_text(HARNESS)
            exe=d/'network-test'
            subprocess.run(['gcc','-std=c99','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-I'+str(d),'-I'+str(ROOT/'src/network'),str(d/'test.c'),'-o',str(exe)],check=True)
            subprocess.run([str(exe)],check=True)
