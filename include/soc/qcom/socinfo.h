/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Copyright (c) 2019-2020, The Linux Foundation. All rights reserved.
 */

#ifndef __SOC_QCOM_SOCINFO_H__
#define __SOC_QCOM_SOCINFO_H__

#include <linux/types.h>

#if IS_ENABLED(CONFIG_QCOM_SOCINFO)
uint32_t socinfo_get_id(void);
uint32_t socinfo_get_serial_number(void);
const char *socinfo_get_id_string(void);
#if defined(CONFIG_MACH_XIAOMI_SM8150)
#define HARDWARE_PLATFORM_UNKNOWN 0
#define HARDWARE_PLATFORM_CEPHEUS 1
#define HARDWARE_PLATFORM_ANDROMEDA 3
#define HARDWARE_PLATFORM_RAPHAEL 4
#define HARDWARE_PLATFORM_VAYU 6

#define HW_MAJOR_VERSION_SHIFT 16
#define HW_MAJOR_VERSION_MASK  0xFFFF0000
#define HW_MINOR_VERSION_SHIFT 0
#define HW_MINOR_VERSION_MASK  0x0000FFFF
#define HW_COUNTRY_VERSION_MASK 0xFFF00000
#define HW_COUNTRY_VERSION_SHIFT 20
#define HW_BUILD_VERSION_MASK 0x000F0000
#define HW_BUILD_VERSION_SHIFT 16

typedef enum {
  CountryCN = 0,
  CountryGlobal = 1,
  CountryIndia = 2,
  INVALID,
} CountryType;

uint32_t get_hw_version_platform(void);
uint32_t get_hw_country_version(void);
uint32_t get_hw_version_major(void);
uint32_t get_hw_version_minor(void);
uint32_t get_hw_version_build(void);
const char *product_name_get(void);
#endif
#else
static inline uint32_t socinfo_get_id(void)
{
	return 0;
}

static inline uint32_t socinfo_get_serial_number(void)
{
	return 0;
}

static inline const char *socinfo_get_id_string(void)
{
	return "N/A";
}
#if defined(CONFIG_MACH_XIAOMI_SM8150)
static inline uint32_t get_hw_version_platform(void);
{
	return 0;
}
static inline uint32_t get_hw_country_version(void);
{
	return 0;
}
static inline uint32_t get_hw_version_major(void);
{
	return 0;
}
static inline uint32_t get_hw_version_minor(void);
{
	return 0;
}
static inline uint32_t get_hw_version_build(void);
{
	return 0;
}
static inline const char *product_name_get(void);
{
	return "N/A";
}
#endif
#endif /* CONFIG_QCOM_SOCINFO */

#endif /* __SOC_QCOM_SOCINFO_H__ */
