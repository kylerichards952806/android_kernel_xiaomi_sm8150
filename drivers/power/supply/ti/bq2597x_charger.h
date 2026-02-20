/*
 * BQ2570x battery charging driver header
 *
 * Copyright (C) 2017 Texas Instruments *
 * Copyright (c) 2025 Aman, duckyduckg65@gmail.com
 * This package is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.

 * THIS PACKAGE IS PROVIDED ``AS IS'' AND WITHOUT ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, WITHOUT LIMITATION, THE IMPLIED
 * WARRANTIES OF MERCHANTIBILITY AND FITNESS FOR A PARTICULAR PURPOSE.
 */

#ifndef __BQ2597X_CHARGER_H
#define __BQ2597X_CHARGER_H

#include <linux/delay.h>
#include <linux/power_supply.h>

#include "bq2597x_charger_iio.h"

/* check_vbus_error */
enum {
	VBUS_ERROR_NONE,
	VBUS_ERROR_LOW,
	VBUS_ERROR_HIGH,
};

/* ADC Channels */
enum {
	ADC_IBUS,
	ADC_VBUS,
	ADC_VAC,
	ADC_VOUT,
	ADC_VBAT,
	ADC_IBAT,
	ADC_TBUS,
	ADC_TBAT,
	ADC_TDIE,
	ADC_MAX_NUM,
};

/* BQ charger roles */
#define BQ25970_ROLE_STDALONE 0
#define BQ25970_ROLE_SLAVE 1
#define BQ25970_ROLE_MASTER 2

enum {
	BQ25970_STDALONE,
	BQ25970_SLAVE,
	BQ25970_MASTER,
};

static int bq2597x_mode_data[] = {
	[BQ25970_STDALONE] = BQ25970_STDALONE,
	[BQ25970_MASTER] = BQ25970_ROLE_MASTER,
	[BQ25970_SLAVE] = BQ25970_ROLE_SLAVE,
};

/* fault registers */
#define BAT_OVP_ALARM BIT(7)
#define BAT_OCP_ALARM BIT(6)
#define BUS_OVP_ALARM BIT(5)
#define BUS_OCP_ALARM BIT(4)
#define BAT_UCP_ALARM BIT(3)
#define VBUS_INSERT BIT(2)
#define VBAT_INSERT BIT(1)
#define ADC_DONE BIT(0)

#define BAT_OVP_FAULT BIT(7)
#define BAT_OCP_FAULT BIT(6)
#define BUS_OVP_FAULT BIT(5)
#define BUS_OCP_FAULT BIT(4)
#define TBUS_TBAT_ALARM BIT(3)
#define TS_BAT_FAULT BIT(2)
#define TS_BUS_FAULT BIT(1)
#define TS_DIE_FAULT BIT(0)

/*below used for comm with other module*/
#define BAT_OVP_FAULT_SHIFT 0
#define BAT_OCP_FAULT_SHIFT 1
#define BUS_OVP_FAULT_SHIFT 2
#define BUS_OCP_FAULT_SHIFT 3
#define BAT_THERM_FAULT_SHIFT 4
#define BUS_THERM_FAULT_SHIFT 5
#define DIE_THERM_FAULT_SHIFT 6

#define BAT_OVP_FAULT_MASK (1 << BAT_OVP_FAULT_SHIFT)
#define BAT_OCP_FAULT_MASK (1 << BAT_OCP_FAULT_SHIFT)
#define BUS_OVP_FAULT_MASK (1 << BUS_OVP_FAULT_SHIFT)
#define BUS_OCP_FAULT_MASK (1 << BUS_OCP_FAULT_SHIFT)
#define BAT_THERM_FAULT_MASK (1 << BAT_THERM_FAULT_SHIFT)
#define BUS_THERM_FAULT_MASK (1 << BUS_THERM_FAULT_SHIFT)
#define DIE_THERM_FAULT_MASK (1 << DIE_THERM_FAULT_SHIFT)

#define BAT_OVP_ALARM_SHIFT 0
#define BAT_OCP_ALARM_SHIFT 1
#define BUS_OVP_ALARM_SHIFT 2
#define BUS_OCP_ALARM_SHIFT 3
#define BAT_THERM_ALARM_SHIFT 4
#define BUS_THERM_ALARM_SHIFT 5
#define DIE_THERM_ALARM_SHIFT 6
#define BAT_UCP_ALARM_SHIFT 7

#define BAT_OVP_ALARM_MASK (1 << BAT_OVP_ALARM_SHIFT)
#define BAT_OCP_ALARM_MASK (1 << BAT_OCP_ALARM_SHIFT)
#define BUS_OVP_ALARM_MASK (1 << BUS_OVP_ALARM_SHIFT)
#define BUS_OCP_ALARM_MASK (1 << BUS_OCP_ALARM_SHIFT)
#define BAT_THERM_ALARM_MASK (1 << BAT_THERM_ALARM_SHIFT)
#define BUS_THERM_ALARM_MASK (1 << BUS_THERM_ALARM_SHIFT)
#define DIE_THERM_ALARM_MASK (1 << DIE_THERM_ALARM_SHIFT)
#define BAT_UCP_ALARM_MASK (1 << BAT_UCP_ALARM_SHIFT)

#define VBAT_REG_STATUS_SHIFT 0
#define IBAT_REG_STATUS_SHIFT 1

#define VBAT_REG_STATUS_MASK (1 << VBAT_REG_STATUS_SHIFT)
#define IBAT_REG_STATUS_MASK (1 << VBAT_REG_STATUS_SHIFT)

#define bq_err(fmt, ...)                                                      \
	do {                                                                  \
		if (bq->mode == BQ25970_ROLE_MASTER)                          \
			printk(KERN_ERR "[bq2597x-MASTER]:%s:" fmt, __func__, \
			       ##__VA_ARGS__);                                \
		else if (bq->mode == BQ25970_ROLE_SLAVE)                      \
			printk(KERN_ERR "[bq2597x-SLAVE]:%s:" fmt, __func__,  \
			       ##__VA_ARGS__);                                \
		else                                                          \
			printk(KERN_ERR "[bq2597x-STANDALONE]:%s:" fmt,       \
			       __func__, ##__VA_ARGS__);                      \
	} while (0);

#define bq_info(fmt, ...)                                                      \
	do {                                                                   \
		if (bq->mode == BQ25970_ROLE_MASTER)                           \
			printk(KERN_INFO "[bq2597x-MASTER]:%s:" fmt, __func__, \
			       ##__VA_ARGS__);                                 \
		else if (bq->mode == BQ25970_ROLE_SLAVE)                       \
			printk(KERN_INFO "[bq2597x-SLAVE]:%s:" fmt, __func__,  \
			       ##__VA_ARGS__);                                 \
		else                                                           \
			printk(KERN_INFO "[bq2597x-STANDALONE]:%s:" fmt,       \
			       __func__, ##__VA_ARGS__);                       \
	} while (0);

#define bq_dbg(fmt, ...)                                                       \
	do {                                                                   \
		if (bq->mode == BQ25970_ROLE_MASTER)                           \
			printk(KERN_DEBUG "[bq2597x-MASTER]:%s:" fmt,          \
			       __func__, ##__VA_ARGS__);                       \
		else if (bq->mode == BQ25970_ROLE_SLAVE)                       \
			printk(KERN_DEBUG "[bq2597x-SLAVE]:%s:" fmt, __func__, \
			       ##__VA_ARGS__);                                 \
		else                                                           \
			printk(KERN_DEBUG "[bq2597x-STANDALONE]:%s:" fmt,      \
			       __func__, ##__VA_ARGS__);                       \
	} while (0);

enum hvdcp3_type {
	HVDCP3_NONE = 0,
	HVDCP3_CLASSA_18W,
	HVDCP3_CLASSB_27W,
	HVDCP3P5_CLASSA_18W,
	HVDCP3P5_CLASSB_27W,
};

#define BUS_OVP_FOR_QC 10000
#define BUS_OVP_ALARM_FOR_QC 9500
#define BUS_OCP_FOR_QC_CLASS_A 3250
#define BUS_OCP_ALARM_FOR_QC_CLASS_A 2000
#define BUS_OCP_FOR_QC_CLASS_B 3750
#define BUS_OCP_ALARM_FOR_QC_CLASS_B 2800
#define BUS_OCP_FOR_QC3P5_CLASS_A 3000
#define BUS_OCP_ALARM_FOR_QC3P5_CLASS_A 2500
#define BUS_OCP_FOR_QC3P5_CLASS_B 3500
#define BUS_OCP_ALARM_FOR_QC3P5_CLASS_B 3200

/*end*/

struct bq2597x_cfg {
	bool bat_ovp_disable;
	bool bat_ocp_disable;
	bool bat_ovp_alm_disable;
	bool bat_ocp_alm_disable;

	int bat_ovp_th;
	int bat_ovp_alm_th;
	int bat_ocp_th;
	int bat_ocp_alm_th;

	bool bus_ovp_alm_disable;
	bool bus_ocp_disable;
	bool bus_ocp_alm_disable;

	int bus_ovp_th;
	int bus_ovp_alm_th;
	int bus_ocp_th;
	int bus_ocp_alm_th;

	bool bat_ucp_alm_disable;

	int bat_ucp_alm_th;
	int ac_ovp_th;

	bool bat_therm_disable;
	bool bus_therm_disable;
	bool die_therm_disable;

	int bat_therm_th; /*in %*/
	int bus_therm_th; /*in %*/
	int die_therm_th; /*in degC*/

	int sense_r_mohm;
};

/* main */
struct bq2597x {
	struct device *dev;
	struct i2c_client *client;

	struct iio_dev		*indio_dev;
	struct iio_chan_spec	*iio_chan;
	struct iio_channel	*int_iio_chans;

	int part_no;
	int revision;

	int mode;

	struct mutex data_lock;
	struct mutex i2c_rw_lock;
	struct mutex charging_disable_lock;
	struct mutex irq_complete;

	bool irq_waiting;
	bool irq_disabled;
	bool resume_completed;

	bool batt_present;
	bool vbus_present;

	bool usb_present;
	bool charge_enabled; /* Register bit status */

	/* ADC reading */
	int vbat_volt;
	int vbus_volt;
	int vout_volt;
	int vac_volt;

	int ibat_curr;
	int ibus_curr;

	int bat_temp;
	int bus_temp;
	int die_temp;

	/* alarm/fault status */
	bool bat_ovp_fault;
	bool bat_ocp_fault;
	bool bus_ovp_fault;
	bool bus_ocp_fault;

	bool bat_ovp_alarm;
	bool bat_ocp_alarm;
	bool bus_ovp_alarm;
	bool bus_ocp_alarm;

	bool bat_ucp_alarm;

	bool bat_therm_alarm;
	bool bus_therm_alarm;
	bool die_therm_alarm;

	bool bat_therm_fault;
	bool bus_therm_fault;
	bool die_therm_fault;

	bool therm_shutdown_flag;
	bool therm_shutdown_stat;

	bool vbat_reg;
	bool ibat_reg;

	int prev_alarm;
	int prev_fault;

	int chg_ma;
	int chg_mv;

	int charge_state;

	struct bq2597x_cfg *cfg;

	int skip_writes;
	int skip_reads;

	struct bq2597x_platform_data *platform_data;

	struct delayed_work monitor_work;

	struct dentry *debug_root;

	struct power_supply_desc psy_desc;
	struct power_supply_config psy_cfg;
	struct power_supply *fc2_psy;
};

/* main functions */
int bq2597x_enable_charge(struct bq2597x *bq, bool enable);
int bq2597x_enable_wdt(struct bq2597x *bq, bool enable);
int bq2597x_set_wdt(struct bq2597x *bq, int ms);
int bq2597x_enable_batovp(struct bq2597x *bq, bool enable);
int bq2597x_set_batovp_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_batovp_alarm(struct bq2597x *bq, bool enable);
int bq2597x_set_batovp_alarm_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_batocp(struct bq2597x *bq, bool enable);
int bq2597x_set_batocp_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_batocp_alarm(struct bq2597x *bq, bool enable);
int bq2597x_set_batocp_alarm_th(struct bq2597x *bq, int threshold);
int bq2597x_set_busovp_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_busovp_alarm(struct bq2597x *bq, bool enable);
int bq2597x_set_busovp_alarm_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_busocp(struct bq2597x *bq, bool enable);
int bq2597x_set_busocp_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_busocp_alarm(struct bq2597x *bq, bool enable);
int bq2597x_set_busocp_alarm_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_batucp_alarm(struct bq2597x *bq, bool enable);
int bq2597x_set_batucp_alarm_th(struct bq2597x *bq, int threshold);
int bq2597x_set_acovp_th(struct bq2597x *bq, int threshold);
int bq2597x_enable_bat_therm(struct bq2597x *bq, bool enable);
int bq2597x_set_bat_therm_th(struct bq2597x *bq, u8 threshold);
int bq2597x_enable_bus_therm(struct bq2597x *bq, bool enable);
int bq2597x_set_bus_therm_th(struct bq2597x *bq, u8 threshold);
int bq2597x_enable_die_therm(struct bq2597x *bq, bool enable);
int bq2597x_set_die_therm_th(struct bq2597x *bq, u8 threshold);
int bq2597x_enable_adc(struct bq2597x *bq, bool enable);
int bq2597x_set_adc_average(struct bq2597x *bq, bool avg);
int bq2597x_set_adc_scanrate(struct bq2597x *bq, bool oneshot);
int bq2597x_set_adc_bits(struct bq2597x *bq, int bits);
int bq2597x_get_adc_data(struct bq2597x *bq, int channel, int *result);
int bq2597x_set_alarm_int_mask(struct bq2597x *bq, u8 mask);
int bq2597x_clear_alarm_int_mask(struct bq2597x *bq, u8 mask);
int bq2597x_set_fault_int_mask(struct bq2597x *bq, u8 mask);
int bq2597x_clear_fault_int_mask(struct bq2597x *bq, u8 mask);
void bq2597x_dump_reg(struct bq2597x *bq);

#endif
