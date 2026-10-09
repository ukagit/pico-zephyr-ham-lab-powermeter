/* DL2DBG HamLab Powermeter: 1N4148 detectors, ADS1115, OLED, shell + HTTP.
 * Software I2C on GP0 (SDA) / GP1 (SCL).
 */
#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/adc.h>
#include "current_calibration.h"
#include <zephyr/shell/shell.h>
#include <zephyr/net/socket.h>
#include <zephyr/logging/log.h>
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>
#include "network/network.h"
#include "network/ntp_clock.h"
#include "hamlab_version.h"
#include "power_calibration.h"
#include "oled_font.h"
#include "hamlab_web.h"
LOG_MODULE_REGISTER(hamlab, LOG_LEVEL_INF);
#define PORT 8080
#define STATE_JSON_SIZE 4608
#define I2C_ADDR 0x48
#define I2C_SDA_PIN 0
#define I2C_SCL_PIN 1
#define OLED_ADDR 0x3c
#define ENC_CLK_PIN 15
#define ENC_DT_PIN 14
#define ENC_BUTTON_PIN 13
static const struct device *gpio = DEVICE_DT_GET(DT_NODELABEL(gpio0));
#define DELAY() k_busy_wait(5)
static K_MUTEX_DEFINE(lock);
static int measurement_error = -ENODEV;
static bool power_peak_valid;
static double power_peak_w;
static bool a2_peak_valid;
static double a2_peak_w;
static int64_t a2_peak_deadline;
static int64_t power_peak_deadline;
static bool swr_peak_valid;
static double swr_peak;
static int64_t swr_peak_deadline;
static int64_t last_measurement_unix_ms;
static double last_measurement_w, last_measurement_swr;
static bool last_measurement_swr_valid;
static bool boot_ap;
static int boot_network_error;
static int64_t boot_notice_until;
static uint8_t oled_view; /* GP19 cycles A0/A2 power/A2 volts; GP20 full, GP21 battery. Encoder: all five. */
/* One-cell Li-ion, 10k top / 10k bottom; ADC input is half battery voltage. */
#define BATTERY_DIVIDER_RATIO 2.0
static bool battery_valid;
static double battery_adc_v, battery_v;
static int battery_error = -ENODATA;
static int64_t battery_next;
static const struct device *battery_adc = DEVICE_DT_GET(DT_NODELABEL(adc));
static int battery_setup_error = -ENODEV;
static const struct adc_channel_cfg battery_cfg = {
    .gain=ADC_GAIN_1, .reference=ADC_REF_INTERNAL,
    .acquisition_time=ADC_ACQ_TIME_DEFAULT, .channel_id=2,
};
static void battery_measure(void) {
    uint16_t raw=0;
    struct adc_sequence seq={.channels=BIT(2),.buffer=&raw,
        .buffer_size=sizeof(raw),.resolution=12};
    int rc=battery_setup_error;
    if(!rc)rc=adc_read(battery_adc,&seq);
    battery_error=rc;
    battery_valid=!rc&&raw>0&&raw<4095;
    if(battery_valid){
        battery_adc_v=raw*adc_ref_internal(battery_adc)/4096.0/1000.0;
        battery_v=battery_adc_v*BATTERY_DIVIDER_RATIO;
    }
}
static struct { double voltage, dbm, mw, vpp; } meter[3];
static uint8_t adc_range[3];
static int16_t adc_raw[3];
static bool adc_valid[3], adc_overrange[3];
static int adc_error[3];
static const uint16_t adc_fs_mv[]={6144,4096,2048,1024,512,256};
static uint8_t oled_frame[1024];
static bool oled_available;
/* Open-drain emulation: never actively drive I2C lines high. */
static void release_line(int p) { gpio_pin_configure(gpio,p,GPIO_INPUT|GPIO_PULL_UP); DELAY(); }
static void low_line(int p) { gpio_pin_configure(gpio,p,GPIO_OUTPUT_LOW); DELAY(); }
static int read_line(int p) { return gpio_pin_get(gpio,p); }
static void i2c_start(void) { release_line(I2C_SDA_PIN); release_line(I2C_SCL_PIN); low_line(I2C_SDA_PIN); low_line(I2C_SCL_PIN); }
static void i2c_stop(void) { low_line(I2C_SDA_PIN); release_line(I2C_SCL_PIN); release_line(I2C_SDA_PIN); }
static int i2c_bit(int bit) {
    if(bit) release_line(I2C_SDA_PIN); else low_line(I2C_SDA_PIN);
    release_line(I2C_SCL_PIN);
    for(int i=0;i<100 && !read_line(I2C_SCL_PIN);i++) DELAY();
    if(!read_line(I2C_SCL_PIN)) { low_line(I2C_SCL_PIN); return -ETIMEDOUT; }
    int result=read_line(I2C_SDA_PIN); low_line(I2C_SCL_PIN); return result;
}
static int i2c_write(uint8_t v) {
    for(int i=7;i>=0;i--) if(i2c_bit((v>>i)&1)<0) return -ETIMEDOUT;
    return i2c_bit(1)==0 ? 0 : -ENXIO;
}
static int oled_write(uint8_t control,const uint8_t *data,size_t count) {
    i2c_start();
    int rc=i2c_write(OLED_ADDR<<1);
    if(!rc)rc=i2c_write(control);
    for(size_t i=0;!rc && i<count;i++)rc=i2c_write(data[i]);
    i2c_stop();
    return rc;
}
static int oled_command(uint8_t cmd) {return oled_write(0,&cmd,1);}
static int oled_init(void) {
    static const uint8_t commands[]={0xae,0xd5,0x80,0xa8,0x3f,0xd3,0x00,
        0x40,0x8d,0x14,0x20,0x02,0xa1,0xc8,0xda,0x12,0x81,0x7f,
        0xd9,0xf1,0xdb,0x40,0xa4,0xa6,0x2e,0xaf};
    for(size_t i=0;i<ARRAY_SIZE(commands);i++) {
        if(oled_command(commands[i]))return -ENXIO;
    }
    return 0;
}
static void oled_text(int page,int col,const char *s) {
    while(*s && col+6<=128) {
        unsigned char c=(unsigned char)*s++;
        if(c<32||c>126)c='?';
        memcpy(&oled_frame[page*128+col],oled_font[c-32],6);
        col+=6;
    }
}
static int oled_flush(void) {
    for(int page=0;page<8;page++) {
        if(oled_command(0xb0|page)||oled_command(0x00)||oled_command(0x10)||
           oled_write(0x40,&oled_frame[page*128],128))return -EIO;
    }
    return 0;
}
static void oled_pixel(int x,int y) {
    if(x>=0&&x<128&&y>=0&&y<64)oled_frame[(y/8)*128+x]|=1U<<(y%8);
}
static void oled_large(int x,int y,const char *text,int scale) {
    for(;*text;text++,x+=6*scale) {
        unsigned char c=*text;if(c<32||c>126)c='?';
        for(int col=0;col<5;col++)for(int row=0;row<8;row++)
            if(oled_font[c-32][col]&(1U<<row))
                for(int dx=0;dx<scale;dx++)for(int dy=0;dy<scale;dy++)
                    oled_pixel(x+col*scale+dx,y+row*scale+dy);
    }
}
/* Called while the measurement lock is held. No inferred open-load detection. */
static const char *swr_oled_warning(void){
    double pf,pr;
    if(!adc_valid[0]||!adc_valid[1]||adc_overrange[0]||adc_overrange[1])return "SWR ADC FEHLER!";
    if(!forward_power(meter[0].voltage,&pf))return "SWR --";
    if(!swr_calibration_compatible())return "SWR FREQ UNKAL.";
    if(!reverse_power(meter[1].voltage,&pr))return meter[1].voltage<reverse_min_v()?"SWR --":"SWR REV ZU HOCH!";
    return "SWR LAST PRUEFEN!";
}
static void oled_compact_locked(void) {
    char line[32],peak[8]="--",ratio[8]="--";double w=0,pr,swr;
    bool valid=adc_valid[0]&&!adc_overrange[0]&&forward_power(meter[0].voltage,&w);
    bool swr_valid=false;
    double largest=valid?w:0;if(power_peak_valid&&power_peak_w>largest)largest=power_peak_w;
    const int scales[]={10,20,50,100,150};int scale=150;
    for(int i=0;i<5;i++)if(largest<=scales[i]){scale=scales[i];break;}
    snprintf(line,sizeof(line),"POWER / %d W ~7MHz",scale);
    oled_text(0,0,line);
    if(valid&&adc_valid[1]&&!adc_overrange[1]&&reverse_power(meter[1].voltage,&pr)&&swr_calibration_compatible()&&calibrated_swr(w,pr,&swr))
        {swr_valid=true;snprintf(ratio,sizeof(ratio),"%.1f",swr);}
    if(valid&&adc_valid[1]&&!adc_overrange[1]&&swr_calibration_compatible()&&isfinite(meter[1].voltage)&&meter[1].voltage>=0&&meter[1].voltage<reverse_min_v())snprintf(ratio,sizeof(ratio),"~1");
    if(valid)snprintf(line,sizeof(line),w<9.95?"%.1f":"%.0f",w);else snprintf(line,sizeof(line),"--");
    /* W is small; power and SWR share the large line below the yellow band. */
    oled_large(0,30,"W",1);
    oled_large(8,18,line,3);
    int end=8+6*3*(int)strlen(line);
    oled_large(end+2,22,"/",2);
    oled_large(end+18,22,ratio,2);
    int fill=valid?(int)(fmin(w,scale)*126/scale):0;
    for(int x=0;x<128;x++){oled_pixel(x,44);oled_pixel(x,51);}
    for(int y=44;y<=51;y++){oled_pixel(0,y);oled_pixel(127,y);}
    for(int x=1;x<=fill;x++)for(int y=46;y<=49;y++)oled_pixel(x,y);
    if(power_peak_valid){int mark=1+(int)(fmin(power_peak_w,scale)*125/scale);
        for(int y=43;y<=53;y++)oled_pixel(mark,y);
        snprintf(peak,sizeof(peak),"%.1f",power_peak_w);}
    snprintf(line,sizeof(line),"MAX %s W",peak);
    if(!swr_valid&&strcmp(swr_oled_warning(),"SWR --")!=0)snprintf(line,sizeof(line),"%s",swr_oled_warning());
    else if(swr>3)snprintf(line,sizeof(line),"SWR > 3 !");
    oled_text(7,0,line); /* warning replaces MAX footer while SWR invalid */
}
static void oled_a2_locked(bool volts) {
    char line[32];double w=0;
    bool overflow=adc_overrange[2]||(adc_valid[2]&&meter[2].voltage>=3.2);
    bool valid=adc_valid[2]&&!overflow&&(volts||current_power(meter[2].voltage,&w));
    bool milli=!volts&&CURRENT_MAX_W<1;
    double factor=milli?1000:1,value=volts?meter[2].voltage:w*factor;
    double peak=a2_peak_w*factor,largest=valid?value:0;
    if(!volts&&a2_peak_valid&&peak>largest)largest=peak;
    const double vs[]={0.1,0.2,0.5,1,2,3.3};
    const double ps[]={10,20,50,100,150,200,250,500,1000};
    double scale=volts?3.3:milli?1000:150;
    for(int i=0;i<(volts?6:milli?9:5);i++) {
        double n=volts?vs[i]:ps[i];if(largest<=n){scale=n;break;}
    }
    const char *unit=volts?"V":milli?"mW":"W";
    snprintf(line,sizeof(line),"A2 %s / %.1f%s",volts?"VOLT":"POWER",scale,unit);
    oled_text(0,0,line);
    if(overflow)snprintf(line,sizeof(line),"OVFL");
    else if(valid)snprintf(line,sizeof(line),volts?"%.3f":"%.2f",value);
    else snprintf(line,sizeof(line),"--");
    oled_large(0,16,line,3);oled_text(4,104,unit);
    if(!volts&&valid&&w>0)snprintf(line,sizeof(line),"%.2f dBm",10.0*log10(w*1000.0));
    else snprintf(line,sizeof(line),volts?"DC direkt 1:1":"-- dBm");
    oled_text(5,0,line);
    int fill=overflow?126:valid?(int)(fmax(0,fmin(value,scale))*126/scale):0;
    for(int x=0;x<128;x++){oled_pixel(x,48);oled_pixel(x,54);}
    for(int y=48;y<=54;y++){oled_pixel(0,y);oled_pixel(127,y);}
    for(int x=1;x<=fill;x++)for(int y=50;y<=52;y++)oled_pixel(x,y);
    if(!volts&&a2_peak_valid){int mark=1+(int)(fmin(peak,scale)*125/scale);for(int y=47;y<=55;y++)oled_pixel(mark,y);}
    if(overflow)snprintf(line,sizeof(line),"OVERFLOW >=3.2V / ADC");
    else if(!valid)snprintf(line,sizeof(line),adc_valid[2]?"Ausserhalb Kennlinie":"ADC FEHLER");
    else if(!volts&&a2_peak_valid)snprintf(line,sizeof(line),"MAX %.2f %s",peak,unit);
    else snprintf(line,sizeof(line),"A2 %.4f V",meter[2].voltage);
    oled_text(7,0,line);
}
static void oled_render_locked(void) {
    char line[32];
    memset(oled_frame,0,sizeof(oled_frame));
    if(k_uptime_get()<boot_notice_until) {
        oled_text(0,0,"HAMLAB NETWORK");
        oled_text(2,0,boot_ap?"AP: HamLab-DL2DBG":"WIFI: saved network");
        if(boot_network_error) {
            snprintf(line,sizeof(line),"START ERROR %d",boot_network_error);
            oled_text(4,0,line);
        } else if(boot_ap) {
            oled_text(4,0,"OPEN / NO PASSWORD");
            oled_text(6,0,"192.168.4.1:8080");
        } else oled_text(4,0,"Connecting...");
        if(oled_flush())oled_available=false;
        return;
    }
    if(oled_view==0) {
        oled_compact_locked();
        if(oled_flush())oled_available=false;
        return;
    }
    if(oled_view==3||oled_view==4) {
        oled_a2_locked(oled_view==4);
        if(oled_flush())oled_available=false;
        return;
    }
    if(oled_view==2) {
        oled_text(0,0,"AKKU 1S / 1800 mAh");
        if(battery_valid)snprintf(line,sizeof(line),"%.2f V",battery_v);
        else snprintf(line,sizeof(line),"-- V");
        oled_large(0,16,line,3);
        if(battery_valid)snprintf(line,sizeof(line),"GP28 %.3f V",battery_adc_v);
        else snprintf(line,sizeof(line),"GP28 fehlt / Fehler");
        oled_text(6,0,line);
        if(oled_flush())oled_available=false;
        return;
    }
    oled_text(0,0,"HAMLAB POWERMETER");
    double cw;
    if(adc_valid[2]&&!adc_overrange[2]&&current_power(meter[2].voltage,&cw))snprintf(line,sizeof(line),cw<1?"A2 %.2fmW %.1fdBm":"A2 %.2fW %.1fdBm",cw<1?cw*1000.0:cw,10.0*log10(cw*1000.0));
    else if(adc_valid[2])snprintf(line,sizeof(line),"I50 --W %.4fV",meter[2].voltage);
    else snprintf(line,sizeof(line),"I50 ADC error");
    oled_text(1,0,line);
    if(measurement_error==0) {
        snprintf(line,sizeof(line),"FWD %+.5f V",meter[0].voltage);
        oled_text(3,0,line);
        snprintf(line,sizeof(line),"REV %+.5f V",meter[1].voltage);
        oled_text(4,0,line);
        double w;
        if(adc_valid[0]&&!adc_overrange[0]&&forward_power(meter[0].voltage,&w))
            snprintf(line,sizeof(line),"P %.1f W ~7MHz",w);
        else snprintf(line,sizeof(line),"P -- outside cal");
        oled_text(5,0,line);
    } else {
        oled_text(3,0,"FWD ADC error");
        oled_text(4,0,"REV ADC error");
    }
    if(power_peak_valid)snprintf(line,sizeof(line),"PEAK %.1f W",power_peak_w);
    else snprintf(line,sizeof(line),"PEAK -- W");
    oled_text(6,0,line);
    double pf,pr,swr;
    if(adc_valid[0]&&adc_valid[1]&&!adc_overrange[0]&&!adc_overrange[1]&&
       forward_power(meter[0].voltage,&pf)&&reverse_power(meter[1].voltage,&pr)&&swr_calibration_compatible()&&calibrated_swr(pf,pr,&swr))
        snprintf(line,sizeof(line),"SWR %.2f ~",swr);
    else if(adc_valid[0]&&adc_valid[1]&&!adc_overrange[0]&&!adc_overrange[1]&&forward_power(meter[0].voltage,&pf)&&swr_calibration_compatible()&&isfinite(meter[1].voltage)&&meter[1].voltage>=0&&meter[1].voltage<reverse_min_v())snprintf(line,sizeof(line),"SWR ~1 (ANNAHME)");
    else snprintf(line,sizeof(line),"%s",swr_oled_warning());
    oled_text(7,0,line);
    if(oled_flush())oled_available=false;
}
static int i2c_read(bool ack) {
    uint8_t v=0;
    for(int i=0;i<8;i++) { int b=i2c_bit(1); if(b<0)return b; v=(v<<1)|b; }
    if(i2c_bit(!ack)<0)return -ETIMEDOUT;
    return v;
}
static int ads_write_config(uint16_t config) {
    i2c_start(); int rc=i2c_write(I2C_ADDR<<1);
    if(!rc)rc=i2c_write(1);
    if(!rc)rc=i2c_write(config>>8);
    if(!rc)rc=i2c_write(config&255);
    i2c_stop(); return rc;
}
static int ads_read_reg(uint8_t reg, uint16_t *out) {
    i2c_start(); int rc=i2c_write(I2C_ADDR<<1);
    if(!rc)rc=i2c_write(reg);
    if(rc) { i2c_stop();return rc; }
    i2c_start(); rc=i2c_write((I2C_ADDR<<1)|1);
    int hi=-1,lo=-1;
    if(!rc)hi=i2c_read(true);
    if(hi>=0)lo=i2c_read(false);
    i2c_stop();
    if(rc)return rc;
    if(hi<0||lo<0)return -EIO;
    *out=(hi<<8)|lo;return 0;
}
static int ads_sample(int channel,int range,int16_t *raw,bool fast) {
    /* MUX 001=A0-A3, 010=A1-A3, 011=A2-A3; signed single-shot. */
    uint16_t cfg=0x8000 | ((channel+1)<<12) | (range<<9) | 0x0100 |
                 (fast ? 0x00e0 : 0x0080) | 3;
    int rc=ads_write_config(cfg);if(rc)return rc;
    for(int n=0;n<30;n++) {
        k_msleep(2);
        uint16_t status;
        rc=ads_read_reg(1,&status);if(rc)return rc;
        if(status&0x8000) {
            uint16_t value;rc=ads_read_reg(0,&value);if(rc)return rc;
            *raw=(int16_t)value;return 0;
        }
    }
    return -ETIMEDOUT;
}
static int ads_measure(int channel,double *volts,bool fast) {
    adc_valid[channel]=false;adc_overrange[channel]=false;
    int16_t raw;int range=adc_range[channel];
    int rc=ads_sample(channel,range,&raw,fast);if(rc)return rc;
    int magnitude=raw<0?-(int)raw:(int)raw;
    if((magnitude>26214 && range>0)||(magnitude<9800 && range<5)) {
        /* Safe broad-range probe; choose smallest range with <=80% usage. */
        if(range!=0){rc=ads_sample(channel,0,&raw,fast);if(rc)return rc;}
        magnitude=raw<0?-(int)raw:(int)raw;
        int selected=0;
        for(int r=1;r<6;r++)
            if((int64_t)magnitude*6144*100 <= (int64_t)26214*adc_fs_mv[r]*100)selected=r;
        range=selected;
        if(range!=0){rc=ads_sample(channel,range,&raw,fast);if(rc)return rc;}
    }
    /* A rising signal may clip after the probe: broaden and remeasure. */
    while((raw==32767||raw==INT16_MIN) && range>0) {
        range--;rc=ads_sample(channel,range,&raw,fast);if(rc)return rc;
    }
    adc_range[channel]=range;adc_raw[channel]=raw;
    adc_overrange[channel]=(raw==32767||raw==INT16_MIN);
    *volts=(double)raw*adc_fs_mv[range]/32768000.0;
    if(adc_overrange[channel])return -ERANGE;
    adc_valid[channel]=true;return 0;
}
static int measure_locked(bool fast) {
    int result=0;
    for(int c=0;c<3;c++) {
        double voltage=0;
        int rc=ads_measure(c,&voltage,fast);adc_error[c]=rc;
        if(!rc)meter[c].voltage=voltage;
        meter[c].dbm=0;meter[c].mw=0;meter[c].vpp=0;
        if(c<2 && rc && !result)result=rc;
    }
    double w;
    int64_t now=k_uptime_get();
    bool power_valid=adc_valid[0]&&!adc_overrange[0]&&forward_power(meter[0].voltage,&w);
    if(power_valid) {

        if(!power_peak_valid||w>power_peak_w||now>=power_peak_deadline) {
            power_peak_w=w;power_peak_deadline=now+3000;
        }
        power_peak_valid=true;
    } else if(now>=power_peak_deadline)power_peak_valid=false;
    double a2_w;
    bool a2_valid=adc_valid[2]&&!adc_overrange[2]&&current_power(meter[2].voltage,&a2_w);
    if(a2_valid){
        if(!a2_peak_valid||a2_w>a2_peak_w||now>=a2_peak_deadline){a2_peak_w=a2_w;a2_peak_deadline=now+3000;}
        a2_peak_valid=true;
    }else if(now>=a2_peak_deadline)a2_peak_valid=false;
    double reverse_w,swr;
    bool swr_valid=power_valid&&adc_valid[1]&&!adc_overrange[1]&&
        reverse_power(meter[1].voltage,&reverse_w)&&swr_calibration_compatible()&&calibrated_swr(w,reverse_w,&swr);
    if(power_valid) {
        int64_t utc;
        if(hamlab_ntp_now(&utc)) {
            last_measurement_unix_ms=utc;last_measurement_w=w;
            last_measurement_swr_valid=swr_valid;
            if(swr_valid)last_measurement_swr=swr;
        }
    }
    if(!fast&&now>=battery_next) {
        battery_measure();
        battery_next=k_uptime_get()+2000;
    }
    if(swr_valid){
        if(!swr_peak_valid||swr>swr_peak||now>=swr_peak_deadline){swr_peak=swr;swr_peak_deadline=now+3000;}
        swr_peak_valid=true;
    }else if(now>=swr_peak_deadline)swr_peak_valid=false;
    measurement_error=result;return result;
}
static int update_meter(void) {
    k_mutex_lock(&lock,K_FOREVER);
    int rc=measure_locked(false);
    k_mutex_unlock(&lock);
    return rc;
}
static void oled_view_step(int direction) {
    k_mutex_lock(&lock,K_FOREVER);
    oled_view=(oled_view+5+direction)%5;
    k_mutex_unlock(&lock);
}
static void encoder_thread(void *a,void *b,void *c) {
    ARG_UNUSED(a);ARG_UNUSED(b);ARG_UNUSED(c);
    static const int8_t moves[16]={0,-1,1,0,1,0,0,-1,-1,0,0,1,0,1,-1,0};
    int prev=(gpio_pin_get(gpio,ENC_CLK_PIN)<<1)|gpio_pin_get(gpio,ENC_DT_PIN);
    int accumulated=0,button_last=gpio_pin_get(gpio,ENC_BUTTON_PIN);
    int button_stable=button_last;
    int64_t changed=k_uptime_get();
    int last[3]={1,1,1},stable[3]={1,1,1};int64_t change[3]={0};
    while(1) {
        for(int i=0;i<3;i++) {
            int value=gpio_pin_get(gpio,19+i);int64_t now=k_uptime_get();
            if(value<0)continue;
            if(value!=last[i]){last[i]=value;change[i]=now;}
            if(value!=stable[i]&&now-change[i]>=30) {
                stable[i]=value;
                if(value==0){k_mutex_lock(&lock,K_FOREVER);oled_view=i==0?(oled_view==0?3:oled_view==3?4:0):(uint8_t)i;k_mutex_unlock(&lock);}
            }
        }
        int clk=gpio_pin_get(gpio,ENC_CLK_PIN),dt=gpio_pin_get(gpio,ENC_DT_PIN);
        if(clk>=0&&dt>=0) {
            int now=(clk<<1)|dt;
            if(now!=prev) {
                accumulated+=moves[(prev<<2)|now];prev=now;
                /* Two valid edges also cover encoders with half-step detents. */
                if(accumulated>=2){oled_view_step(1);accumulated=0;}
                if(accumulated<=-2){oled_view_step(-1);accumulated=0;}
            }
        }
        int button=gpio_pin_get(gpio,ENC_BUTTON_PIN);
        if(button>=0) {
            if(button!=button_last){button_last=button;changed=k_uptime_get();}
            if(button!=button_stable && k_uptime_get()-changed>=30) {
                button_stable=button;
                if(button==0) {
                    k_mutex_lock(&lock,K_FOREVER);
                    oled_view=(oled_view+1)%3;
                    k_mutex_unlock(&lock);
                }
            }
        }
        k_msleep(2);
    }
}
static void display_thread(void *a,void *b,void *c) {
    ARG_UNUSED(a);ARG_UNUSED(b);ARG_UNUSED(c);
    int64_t next_oled=0;
    while(1) {
        update_meter();
        if(oled_available && k_uptime_get()>=next_oled) {
            k_mutex_lock(&lock,K_FOREVER);
            oled_render_locked();
            k_mutex_unlock(&lock);
            next_oled=k_uptime_get()+400;
        }
        k_msleep(100);
    }
}
/* K_THREAD_DEFINE takes an integer millisecond delay, not k_timeout_t. */
K_THREAD_DEFINE(encoder_id,1536,encoder_thread,NULL,NULL,NULL,6,0,SYS_FOREVER_MS);
K_THREAD_DEFINE(display_id,3072,display_thread,NULL,NULL,NULL,9,0,SYS_FOREVER_MS);
/* Called with meter lock held. SWR below the measured reverse floor stays numerically invalid. */
static void live_swr_json(char *buf,size_t len) {
    double pf,pr,swr;char value[32]="null",peak[32]="null";
    const char *quality="provisional";
    bool valid=false;
    if(!adc_valid[0]||!adc_valid[1]||adc_overrange[0]||adc_overrange[1])quality="adc_error";
    else if(!forward_power(meter[0].voltage,&pf))quality="forward_outside_calibrated_range";
    else if(!reverse_power(meter[1].voltage,&pr))quality=meter[1].voltage<reverse_min_v()?"reverse_below_calibrated_floor":"reverse_above_calibrated_range";
    else if(!swr_calibration_compatible())quality="forward_frequency_not_calibrated";
    else if(!calibrated_swr(pf,pr,&swr))quality="invalid_power_ratio";
    else {valid=true;snprintf(value,sizeof(value),"%.3f",swr);}
    if(swr_peak_valid)snprintf(peak,sizeof(peak),"%.3f",swr_peak);
    snprintf(buf,len,"{\"enabled\":true,\"valid\":%s,\"value\":%s,\"peak\":%s,\"quality\":\"%s\"}",valid?"true":"false",value,peak,quality);
}
static void power_json(char *buf,size_t len) {
    double w=0; char value[32]="null",peak[32]="null",reverse[32]="null";
    bool valid=adc_valid[0]&&!adc_overrange[0]&&forward_power(meter[0].voltage,&w);
    if(valid)snprintf(value,sizeof(value),"%.4f",w);
    if(power_peak_valid)snprintf(peak,sizeof(peak),"%.4f",power_peak_w);
    double rw;
    bool reverse_valid=adc_valid[1]&&!adc_overrange[1]&&reverse_power(meter[1].voltage,&rw);
    if(reverse_valid)snprintf(reverse,sizeof(reverse),"%.4f",rw);
    const char *quality=!adc_valid[0]||adc_overrange[0]?"adc_error":valid?(swr_calibration_compatible()?"provisional":"forward_frequency_not_calibrated"):"outside_calibrated_range";
    snprintf(buf,len,"{\"enabled\":true,\"forward_valid\":%s,\"forward_w\":%s,\"peak_w\":%s,\"reverse_w\":%s,\"quality\":\"%s\",\"calibration_frequency_hz\":7031670,\"frequency_verified\":false,\"reference\":\"scope_vpp_sine_50ohm\",\"min_w\":%.6f,\"max_w\":%.6f,\"reverse_valid\":%s,\"reverse_calibration_frequency_hz\":%u,\"reverse_min_w\":%.4f,\"reverse_max_w\":%.4f,\"reverse_calibration\":\"provisional_reversed_coupler\"}",valid?"true":"false",value,peak,reverse,quality,hamlab_curve(CURVE_FORWARD)->points[0].w,hamlab_curve(CURVE_FORWARD)->points[hamlab_curve(CURVE_FORWARD)->count-1].w,reverse_valid?"true":"false",reverse_calibration_hz,reverse_min_w(),reverse_max_w());
}
static int state_json(char *buf,size_t len) {
    if(k_mutex_lock(&lock,K_MSEC(250))) {
        snprintf(buf,len,"{\"measurement_valid\":false,\"measurement_error\":%d}",-EBUSY);
        return -EBUSY;
    }
    /* Shared scratch is used only while lock is held; no 2 KiB stack frame. */
    static char channels[3][400],power[768],clock_json[320],swr_json[256],battery_json[256],current_json[512];
    live_swr_json(swr_json,sizeof(swr_json));
    int64_t utc;bool synced=hamlab_ntp_now(&utc);
    char stamp[32]="null",last_w[32]="null",last_swr[32]="null";
    if(last_measurement_unix_ms) {
        snprintf(stamp,sizeof(stamp),"%lld",(long long)last_measurement_unix_ms);
        snprintf(last_w,sizeof(last_w),"%.4f",last_measurement_w);
    }
    if(last_measurement_unix_ms&&last_measurement_swr_valid)snprintf(last_swr,sizeof(last_swr),"%.3f",last_measurement_swr);
    snprintf(clock_json,sizeof(clock_json),"{\"synced\":%s,\"source\":\"ntp\",\"last_measurement_unix_ms\":%s,\"last_forward_w\":%s,\"last_swr\":%s}",synced?"true":"false",stamp,last_w,last_swr);
    char bv[32]="null",av[32]="null";
    if(battery_valid){snprintf(bv,sizeof(bv),"%.4f",battery_v);snprintf(av,sizeof(av),"%.4f",battery_adc_v);}
    snprintf(battery_json,sizeof(battery_json),"{\"valid\":%s,\"error\":%d,\"input\":\"GP28/ADC2\",\"voltage_v\":%s,\"adc_voltage_v\":%s,\"divider_ratio\":2,\"nominal_capacity_mah\":1800}",battery_valid?"true":"false",battery_error,bv,av);
    power_json(power,sizeof(power));
    for(int c=0;c<3;c++) {
        char voltage[40]="null",raw[24]="null",input_voltage[40]="null";
        if(c==2&&adc_valid[c]&&!adc_overrange[c])snprintf(input_voltage,sizeof(input_voltage),"%.7f",meter[c].voltage);
        if(adc_valid[c])snprintf(voltage,sizeof(voltage),"%.7f",meter[c].voltage);
        if(adc_valid[c]||adc_overrange[c])snprintf(raw,sizeof(raw),"%d",adc_raw[c]);
        snprintf(channels[c],sizeof(channels[c]),"{\"role\":\"%s\",\"input\":\"A%d-A3\",\"valid\":%s,\"error\":%d,\"overrange\":%s,\"raw\":%s,\"range_mv\":%u,\"lsb_uv\":%.4f,\"voltage_v\":%s,\"divider_ratio\":%u,\"input_voltage_v\":%s,\"voltage_overflow\":%s,\"calibrated\":false,\"dbm\":null,\"mw\":null,\"vpp\":null}",
            c==2?"current":c?"reverse":"forward",c,adc_valid[c]?"true":"false",adc_error[c],adc_overrange[c]?"true":"false",raw,adc_fs_mv[adc_range[c]],adc_fs_mv[adc_range[c]]/32.768,voltage,1U,input_voltage,c==2&&(adc_overrange[c]||(adc_valid[c]&&meter[c].voltage>=3.2))?"true":"false");
    }
    double cw=0;bool cv=adc_valid[2]&&!adc_overrange[2]&&current_power(meter[2].voltage,&cw);
    char watts[32]="null",a2_peak[32]="null",dbm[32]="null";
    if(cv&&cw>0)snprintf(dbm,sizeof(dbm),"%.4f",10.0*log10(cw*1000.0));
    if(a2_peak_valid)snprintf(a2_peak,sizeof(a2_peak),"%.6f",a2_peak_w);
    if(cv)snprintf(watts,sizeof(watts),"%.4f",cw);
    snprintf(current_json,sizeof(current_json),"{\"input\":\"A2-A3\",\"valid\":%s,\"power_50ohm_w\":%s,\"power_dbm\":%s,\"peak_w\":%s,\"calibration_frequency_hz\":%u,\"frequency_verified\":false,\"assumed_load_ohms\":50,\"master\":\"%s\",\"min_w\":%.6f,\"max_w\":%.6f,\"quality\":\"%s\"}",cv?"true":"false",watts,dbm,a2_peak,hamlab_curve(CURVE_CURRENT)->frequency_hz,curve_master(CURVE_CURRENT,hamlab_curve(CURVE_CURRENT)->frequency_hz),CURRENT_MIN_W,CURRENT_MAX_W,!adc_valid[2]||adc_overrange[2]?"adc_error":cv?(hamlab_curve(CURVE_CURRENT)->frequency_hz==1000000?"provisional_scope_50ohm":meter[2].voltage>=CURRENT_PLATEAU_V?"aligned_to_a0_upper_plateau":"aligned_to_a0_50ohm_only"):"outside_calibrated_range");
    int n=snprintf(buf,len,"{\"name\":\"pico-zephyr-ham-lab-powermeter\",\"measurement_valid\":%s,\"measurement_error\":%d,\"autorange\":true,\"channels\":[%s,%s,%s],\"swr\":%s,\"power\":%s,\"time\":%s,\"battery\":%s,\"current_coupler\":%s,\"curves_source\":\"%s\",\"curve_profiles\":{\"forward\":\"%s\",\"reverse_7mhz\":\"%s\",\"reverse_50mhz\":\"%s\",\"current\":\"%s\"}}",measurement_error==0?"true":"false",measurement_error,channels[0],channels[1],channels[2],swr_json,power,clock_json,battery_json,current_json,hamlab_curves_from_flash()?"flash":"builtin",hamlab_curve_profile(0),hamlab_curve_profile(1),hamlab_curve_profile(2),hamlab_curve_profile(3));
    if(n<0||(size_t)n>=len) {
        /* Never expose an incomplete JSON document to HTTP or the shell. */
        n=snprintf(buf,len,"{\"measurement_valid\":false,\"measurement_error\":%d}",-ENOSPC);
    }
    k_mutex_unlock(&lock);return n;
}
static K_MUTEX_DEFINE(shell_state_lock);
static int cmd_status(const struct shell *sh,size_t argc,char **argv) {
    ARG_UNUSED(argc);ARG_UNUSED(argv);
    /* USB and dummy/Telnet shell can call concurrently. Keep this 3 KiB off
     * their stacks, serialize output, and release the meter lock before printing. */
    static char json[STATE_JSON_SIZE];
    if(k_mutex_lock(&shell_state_lock,K_MSEC(250))) {
        shell_error(sh,"State output busy; retry");return -EBUSY;
    }
    int rc=state_json(json,sizeof(json));
    shell_print(sh,"%s",json);
    k_mutex_unlock(&shell_state_lock);
    return rc<0?rc:0;
}
static int cmd_info(const struct shell *sh,size_t argc,char **argv) {
    ARG_UNUSED(argc); ARG_UNUSED(argv);
    shell_print(sh,"{\"name\":\"pico-zephyr-ham-lab-powermeter\",\"version\":\"%s\",\"board\":\"rpi_pico/rp2040/w\",\"adc\":\"ADS1115\",\"autorange\":true,\"forward_input\":\"A0-A3\",\"reverse_input\":\"A1-A3\",\"calibrated\":false,\"forward_calibration\":\"provisional\",\"reverse_calibration\":\"provisional_reversed_coupler\",\"reverse_calibration_frequencies_hz\":[7100000,50100000],\"battery_input\":\"GP28/ADC2\",\"current_input\":\"A2-A3\",\"frequency_verified\":false,\"calibration_frequency_hz\":7031670}",HAMLAB_VERSION);
    return 0;
}
static int cmd_meter(const struct shell *sh,size_t argc,char **argv) {
    return cmd_status(sh,argc,argv);
}
/* Read continuously sampled values; never wait indefinitely in a shell command. */
static int cmd_swr(const struct shell *sh,size_t argc,char **argv){
    ARG_UNUSED(argv);
    if(argc!=1)return -EINVAL;
    char json[256];
    if(k_mutex_lock(&lock,K_MSEC(250))){shell_error(sh,"Meter busy; retry hamlab swr");return -EBUSY;}
    live_swr_json(json,sizeof(json));k_mutex_unlock(&lock);
    shell_print(sh,"%s",json);return 0;
}
static int cmd_power(const struct shell *sh,size_t argc,char **argv){
    ARG_UNUSED(argv);
    if(argc!=1)return -EINVAL;
    char json[768];
    if(k_mutex_lock(&lock,K_MSEC(250))){shell_error(sh,"Meter busy; retry hamlab power");return -EBUSY;}
    power_json(json,sizeof(json));k_mutex_unlock(&lock);
    shell_print(sh,"%s",json);return 0;
}
/* Selection concerns reverse calibration only; forward table remains unchanged. */
static int cmd_calibration(const struct shell *sh,size_t argc,char **argv){
    unsigned int hz=0;
    if(argc==2){
        if(strcmp(argv[1],"7100000")==0)hz=7100000;
        else if(strcmp(argv[1],"50100000")==0)hz=50100000;
        else {shell_error(sh,"Use 7100000 or 50100000 Hz");return -EINVAL;}
    }
    if(k_mutex_lock(&lock,K_MSEC(250)))return -EBUSY;
    if(hz){
        reverse_calibration_hz=hz;
        swr_peak_valid=false;power_peak_valid=false;a2_peak_valid=false;
        last_measurement_swr_valid=false;
    }
    hz=reverse_calibration_hz;
    k_mutex_unlock(&lock);
    shell_print(sh,"{\"reverse_calibration_frequency_hz\":%u,\"frequency_verified\":false,\"persistent\":false}",hz);
    return 0;
}
/* Temporary step-1 transport: short hex chunks over USB/Telnet shell.
 * USB MSC is deliberately not enabled in this version. */
static int cmd_curves(const struct shell *sh,size_t argc,char **argv){
    if(k_mutex_lock(&lock,K_MSEC(250))){shell_error(sh,"Meter busy; retry");return -EBUSY;}
    int rc=0;char error[160]="";
    if(argc==1||(argc==2&&!strcmp(argv[1],"status"))){
        shell_print(sh,"{\"source\":\"%s\",\"storage_error\":%d,\"expected_bytes\":%zu,\"received_bytes\":%zu,\"usb_filesystem\":false,\"selected\":{\"forward\":\"%s\",\"reverse_7mhz\":\"%s\",\"reverse_50mhz\":\"%s\",\"current\":\"%s\"}}",hamlab_curves_from_flash()?"flash":"builtin",hamlab_curves_storage_error(),hamlab_curves_expected(),hamlab_curves_received(),hamlab_curve_profile(0),hamlab_curve_profile(1),hamlab_curve_profile(2),hamlab_curve_profile(3));
        for(int i=0;i<CURVES_COUNT;i++){
            const struct curve_data *c=hamlab_curve(i);
            shell_print(sh,"%s [%s]: %u Hz, %u points, %.6f..%.6f V, %.4f..%.4f W",curve_names[i],hamlab_curve_profile(i),c->frequency_hz,c->count,c->points[0].v,c->points[c->count-1].v,c->points[0].w,c->points[c->count-1].w);
        }
    }else if(argc==2&&!strcmp(argv[1],"list")){
        shell_print(sh,"{\"profiles\":[");
        shell_print(sh,"\"builtin\"%s",(hamlab_profiles_count()||hamlab_curves_has_legacy())?",":"");
        if(hamlab_curves_has_legacy())shell_print(sh,"\"legacy\"%s",hamlab_profiles_count()?",":"");
        for(unsigned i=0;i<hamlab_profiles_count();i++)shell_print(sh,"\"%s\"%s",hamlab_profile_name(i),i+1<hamlab_profiles_count()?",":"");
        shell_print(sh,"],\"selected\":{\"forward\":\"%s\",\"reverse_7mhz\":\"%s\",\"reverse_50mhz\":\"%s\",\"current\":\"%s\"}}",hamlab_curve_profile(0),hamlab_curve_profile(1),hamlab_curve_profile(2),hamlab_curve_profile(3));
    }else if(argc==4&&!strcmp(argv[1],"select")){
        int id=-1;for(int i=0;i<CURVES_COUNT;i++)if(!strcmp(argv[2],curve_names[i]))id=i;
        rc=id<0?-EINVAL:hamlab_curves_select(id,argv[3]);
        if(!rc){power_peak_valid=false;a2_peak_valid=false;swr_peak_valid=false;last_measurement_unix_ms=0;last_measurement_swr_valid=false;
            shell_print(sh,"{\"selected\":\"%s\",\"profile\":\"%s\",\"saved\":true}",curve_names[id],hamlab_curve_profile(id));}
    }else if(argc==3&&!strcmp(argv[1],"begin")){
        char *end;errno=0;unsigned long n=strtoul(argv[2],&end,10);
        if(errno||*end||argv[2][0]=='-'||!argv[2][0])rc=-EINVAL;
        else rc=hamlab_curves_begin(n);
        if(!rc)shell_print(sh,"{\"expected_bytes\":%zu,\"received_bytes\":0}",hamlab_curves_expected());
    }else if(argc==3&&!strcmp(argv[1],"chunk")){
        rc=hamlab_curves_chunk(argv[2]);
        if(!rc)shell_print(sh,"{\"received_bytes\":%zu}",hamlab_curves_received());
    }else if(argc==2&&!strcmp(argv[1],"check")){
        rc=hamlab_curves_check(error,sizeof(error));if(!rc)shell_print(sh,"{\"valid\":true,\"saved\":false}");
    }else if(argc==3&&!strcmp(argv[1],"store")){
        rc=hamlab_curves_import_profile(argv[2],error,sizeof(error));
        if(!rc)shell_print(sh,"{\"valid\":true,\"saved\":true,\"activated\":false,\"profile\":\"%s\"}",argv[2]);
    }else if(argc==2&&!strcmp(argv[1],"import")){
        rc=hamlab_curves_import(error,sizeof(error));
        if(!rc){power_peak_valid=false;a2_peak_valid=false;swr_peak_valid=false;last_measurement_unix_ms=0;last_measurement_swr_valid=false;
            shell_print(sh,"{\"valid\":true,\"saved\":true,\"source\":\"flash\"}");}
    }else if(argc==2&&!strcmp(argv[1],"abort")){
        hamlab_curves_abort();shell_print(sh,"{\"aborted\":true}");
    }else if(argc==2&&!strcmp(argv[1],"export")){
        const char *json;rc=hamlab_curves_export(&json);if(rc>=0){shell_print(sh,"%s",json);rc=0;}
    }else{rc=-EINVAL;snprintf(error,sizeof(error),"Use status/list/select <role> <profile>/begin/chunk/check/store <profile>/import/export/abort");}
    k_mutex_unlock(&lock);
    if(rc)shell_error(sh,"Curves error %d: %s",rc,error[0]?error:"transfer/storage busy or invalid argument");
    return rc;
}
SHELL_STATIC_SUBCMD_SET_CREATE(hamlab_cmds,
    SHELL_CMD_ARG(curves,NULL,"JSON curves: status/list/select/begin/chunk/check/store/import/export/abort",cmd_curves,1,3),
    SHELL_CMD_ARG(calibration,NULL,"Reverse curve: 7100000 or 50100000 Hz (RAM only)",cmd_calibration,1,1),
    SHELL_CMD_ARG(power,NULL,"Provisional forward power at 7031670 Hz",cmd_power,1,0),
    SHELL_CMD_ARG(swr,NULL,"Provisional calibrated SWR at 7031670 Hz",cmd_swr,1,0),
    SHELL_CMD_ARG(info,NULL,"Firmware version and calibration",cmd_info,1,0),
    SHELL_CMD_ARG(status,NULL,"Current JSON state",cmd_status,1,0),
    SHELL_CMD_ARG(meter,NULL,"Latest A0-A3/A1-A3 sample, autorange; bounded wait",cmd_meter,1,0),
    SHELL_SUBCMD_SET_END);
SHELL_CMD_REGISTER(hamlab,&hamlab_cmds,"HamLab Powermeter instrument",NULL);
static void send_full(int fd,const char *buf,size_t len) {
    while(len) {
        ssize_t sent=zsock_send(fd,buf,len,0);
        if(sent<=0)return;
        buf+=sent;len-=sent;
    }
}
static void respond(int fd,int code,const char *type,const char *body) {
    char head[256];size_t size=strlen(body);
    int n=snprintf(head,sizeof(head),"HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %zu\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n",code,code==200?"OK":code==400?"Bad Request":code==409?"Conflict":code==503?"Service Unavailable":"Not Found",type,size);
    send_full(fd,head,n);send_full(fd,body,size);
}
static void handle_http(int fd) {
    char req[1024]={0};
    /* Only http_thread calls this handler; response storage is not on its stack. */
    static char json[STATE_JSON_SIZE];
    ssize_t n=zsock_recv(fd,req,sizeof(req)-1,0);if(n<=0)return;
    req[n]=0;
    while(!strstr(req,"\r\n\r\n") && (size_t)n<sizeof(req)-1) {
        ssize_t got=zsock_recv(fd,req+n,sizeof(req)-1-n,0);
        if(got<=0)return;
        n+=got;req[n]=0;
    }
    char *body=strstr(req,"\r\n\r\n");
    if(!body){respond(fd,400,"text/plain","HTTP-Header unvollständig");return;}
    size_t content_length=0;
    for(char *line=req;line<body;) {
        char *next=strstr(line,"\r\n");if(!next||next>body)break;
        if(!strncasecmp(line,"Content-Length:",15))content_length=strtoul(line+15,NULL,10);
        line=next+2;
    }
    if(content_length>sizeof(req)-1-(size_t)(body+4-req)) {
        respond(fd,400,"text/plain","JSON zu groß");return;
    }
    while((size_t)(req+n-(body+4))<content_length) {
        ssize_t got=zsock_recv(fd,req+n,sizeof(req)-1-n,0);
        if(got<=0)return;
        n+=got;req[n]=0;
    }
    if(!strncmp(req,"GET /compact-a2 ",16)||!strncmp(req,"GET /compact-a2.html ",21)){respond(fd,200,"text/html; charset=utf-8",compact_a2_html);return;}
    if(!strncmp(req,"GET /compact ",13) || !strncmp(req,"GET /compact.html ",18)) {respond(fd,200,"text/html; charset=utf-8",compact_html);return;}
    if(!strncmp(req,"GET / ",6)) {respond(fd,200,"text/html; charset=utf-8",html);return;}
    if(!strncmp(req,"POST /api/v1/peak/reset ",24)) {
        k_mutex_lock(&lock,K_FOREVER);power_peak_valid=false;a2_peak_valid=false;power_peak_w=0;swr_peak_valid=false;swr_peak=0;k_mutex_unlock(&lock);
        respond(fd,200,"application/json","{\"reset\":true}");return;
    }
    if(!strncmp(req,"GET /api/v1/measure ",20)) {
        int rc=update_meter();state_json(json,sizeof(json));respond(fd,rc==-EBUSY?409:rc?503:200,"application/json",json);return;
    }
    if(!strncmp(req,"GET /api/v1/curves ",19)) {
        if(k_mutex_lock(&lock,K_MSEC(250))){respond(fd,409,"application/json","{\"error\":\"busy\"}");return;}
        const char *curves;int rc=hamlab_curves_export(&curves);
        if(rc>=0){
            memcpy(json,curves,(size_t)rc-1);
            int n=snprintf(json+rc-1,sizeof(json)-(size_t)rc+1,",\"profiles\":{\"forward\":\"%s\",\"reverse_7mhz\":\"%s\",\"reverse_50mhz\":\"%s\",\"current\":\"%s\"}}",hamlab_curve_profile(0),hamlab_curve_profile(1),hamlab_curve_profile(2),hamlab_curve_profile(3));
            if(n<0||(size_t)n>=sizeof(json)-(size_t)rc+1)rc=-ENOSPC;
        }
        k_mutex_unlock(&lock);
        respond(fd,rc<0?409:200,"application/json",rc<0?"{\"error\":\"curves unavailable during transfer\"}":json);return;
    }
    if(!strncmp(req,"GET /api/v1/state ",18)) {state_json(json,sizeof(json));respond(fd,200,"application/json",json);return;}
    if(!strncmp(req,"GET /api/v1/info ",17)) {
        snprintf(json,sizeof(json),"{\"name\":\"pico-zephyr-ham-lab-powermeter\",\"version\":\"%s\",\"board\":\"rpi_pico/rp2040/w\",\"adc\":\"ADS1115\",\"autorange\":true,\"forward_input\":\"A0-A3\",\"reverse_input\":\"A1-A3\",\"calibrated\":false,\"forward_calibration\":\"provisional\",\"reverse_calibration\":\"provisional_reversed_coupler\",\"reverse_calibration_frequencies_hz\":[7100000,50100000],\"battery_input\":\"GP28/ADC2\",\"current_input\":\"A2-A3\",\"frequency_verified\":false,\"calibration_frequency_hz\":7031670}",HAMLAB_VERSION);
        respond(fd,200,"application/json",json);return;
    }
    respond(fd,404,"text/plain","Not found");
}
static void http_thread(void *arg1, void *arg2, void *arg3) {
    ARG_UNUSED(arg1); ARG_UNUSED(arg2); ARG_UNUSED(arg3);
    int s=zsock_socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s<0){LOG_ERR("socket: %d",errno);return;}
    struct sockaddr_in addr={.sin_family=AF_INET,.sin_port=htons(PORT),.sin_addr.s_addr=INADDR_ANY};
    if(zsock_bind(s,(struct sockaddr *)&addr,sizeof(addr))<0||zsock_listen(s,2)<0){LOG_ERR("HTTP bind/listen: %d",errno);zsock_close(s);return;}
    LOG_INF("HTTP on port %d",PORT);
    while(1) {
        int c=zsock_accept(s,NULL,NULL);if(c<0){k_msleep(100);continue;}
        struct timeval tv={.tv_sec=2};zsock_setsockopt(c,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv));
        handle_http(c);zsock_close(c);
    }
}
K_THREAD_DEFINE(http_id,6144,http_thread,NULL,NULL,NULL,7,0,0);
int main(void) {
    if(!device_is_ready(gpio)){LOG_ERR("GPIO not ready");return 0;}
    /* Sample battery button before any saved WLAN connection is requested. */
    int button_rc=gpio_pin_configure(gpio,21,GPIO_INPUT|GPIO_PULL_UP);
    int boot_button=button_rc?1:gpio_pin_get(gpio,21);
    k_msleep(30);
    boot_ap=boot_button==0&&gpio_pin_get(gpio,21)==0;
    k_mutex_lock(&lock,K_FOREVER);
    int curves_rc=hamlab_curves_init();
    k_mutex_unlock(&lock);
    LOG_INF("Curves source %s, storage status %d",hamlab_curves_from_flash()?"flash":"builtin",curves_rc);
    if(device_is_ready(battery_adc))battery_setup_error=adc_channel_setup(battery_adc,&battery_cfg);
    release_line(I2C_SDA_PIN);release_line(I2C_SCL_PIN);
    gpio_pin_configure(gpio,ENC_CLK_PIN,GPIO_INPUT|GPIO_PULL_UP);
    gpio_pin_configure(gpio,ENC_DT_PIN,GPIO_INPUT|GPIO_PULL_UP);
    gpio_pin_configure(gpio,ENC_BUTTON_PIN,GPIO_INPUT|GPIO_PULL_UP);
    oled_available=(oled_init()==0);
    for(int pin=19;pin<=21;pin++)gpio_pin_configure(gpio,pin,GPIO_INPUT|GPIO_PULL_UP);

    LOG_INF("OLED %s, encoder GP15/GP14, button GP13",oled_available?"ready":"not found");
    int net_rc=hamlab_network_boot(boot_ap);
    boot_network_error=net_rc;
    boot_notice_until=k_uptime_get()+10000;
    k_thread_start(encoder_id);
    k_thread_start(display_id);
    LOG_INF("HamLab Powermeter ready. Network boot result: %d; USB shell: hamlab status", net_rc);
    return 0;
}
