/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Copyright (c) 2025, Aman <duckyduckg65@gmail.com>
 */

#ifndef __BQ2597X_CHARGER_IIO_H
#define __BQ2597X_CHARGER_IIO_H

#include <linux/iio/consumer.h>
#include <linux/iio/iio.h>
#include <dt-bindings/iio/qti_power_supply_iio.h>

struct bq2597x_charger_iio_channels {
	const char *datasheet_name;
	int channel_num;
	enum iio_chan_type type;
	long info_mask;
};

#define BQ2597X_CHARGER_IIO_CHAN(_name, _num, _type, _mask)		\
	{						\
		.datasheet_name = _name,		\
		.channel_num = _num,			\
		.type = _type,				\
		.info_mask = _mask,			\
	},

#define BQ2597X_CHARGER_CHAN_VOLT(_name, _num)			\
	BQ2597X_CHARGER_IIO_CHAN(_name, _num, IIO_VOLTAGE,		\
		BIT(IIO_CHAN_INFO_PROCESSED))

#define BQ2597X_CHARGER_CHAN_CUR(_name, _num)			\
	BQ2597X_CHARGER_IIO_CHAN(_name, _num, IIO_CURRENT,		\
		BIT(IIO_CHAN_INFO_PROCESSED))

#define BQ2597X_CHARGER_CHAN_TEMP(_name, _num)			\
	BQ2597X_CHARGER_IIO_CHAN(_name, _num, IIO_TEMP,		\
		BIT(IIO_CHAN_INFO_PROCESSED))

#define BQ2597X_CHARGER_CHAN_POW(_name, _num)			\
	BQ2597X_CHARGER_IIO_CHAN(_name, _num, IIO_POWER,		\
		BIT(IIO_CHAN_INFO_PROCESSED))

#define BQ2597X_CHARGER_CHAN_INDEX(_name, _num)			\
	BQ2597X_CHARGER_IIO_CHAN(_name, _num, IIO_INDEX,		\
		BIT(IIO_CHAN_INFO_PROCESSED))

#define BQ2597X_CHARGER_CHAN_ACT(_name, _num)			\
	BQ2597X_CHARGER_IIO_CHAN(_name, _num, IIO_ACTIVITY,		\
		BIT(IIO_CHAN_INFO_PROCESSED))

static const struct bq2597x_charger_iio_channels bq2597x_charger_iio_psy_channels[] = {
	BQ2597X_CHARGER_CHAN_ACT("battery_preset", PSY_IIO_BQ_BATTERY_PRESENT)
	BQ2597X_CHARGER_CHAN_ACT("vbus_present", PSY_IIO_BQ_VBUS_PRESENT)
	BQ2597X_CHARGER_CHAN_VOLT("battery_voltage", PSY_IIO_BQ_BATTERY_VOLTAGE)
	BQ2597X_CHARGER_CHAN_CUR("battery_current", PSY_IIO_BQ_BATTERY_CURRENT)
	BQ2597X_CHARGER_CHAN_TEMP("battery_temp", PSY_IIO_BQ_BATTERY_TEMPERATURE)
	BQ2597X_CHARGER_CHAN_VOLT("bus_voltage", PSY_IIO_BQ_BUS_VOLTAGE)
	BQ2597X_CHARGER_CHAN_CUR("bus_current", PSY_IIO_BQ_BUS_CURRENT)
	BQ2597X_CHARGER_CHAN_TEMP("bus_temp", PSY_IIO_BQ_BUS_TEMPERATURE)
	BQ2597X_CHARGER_CHAN_TEMP("die_temp", PSY_IIO_BQ_DIE_TEMPERATURE)
	BQ2597X_CHARGER_CHAN_INDEX("alarm_status", PSY_IIO_BQ_ALARM_STATUS)
	BQ2597X_CHARGER_CHAN_INDEX("fault_status", PSY_IIO_BQ_FAULT_STATUS)
	BQ2597X_CHARGER_CHAN_INDEX("reg_status", PSY_IIO_BQ_REG_STATUS)
    BQ2597X_CHARGER_CHAN_INDEX("bus_protection_qc3", PSY_IIO_BQ_SET_BUS_PROTECTION_FOR_QC3)
    BQ2597X_CHARGER_CHAN_ACT("bus_error_status", PSY_IIO_BQ_BUS_ERROR_STATUS)
    BQ2597X_CHARGER_CHAN_ACT("charging_enabled", PSY_IIO_BQ_CHARGING_ENABLED)
};

struct iio_channel **get_bq_ext_channels(struct device *dev,
	const char *const *channel_map, int size);
#endif