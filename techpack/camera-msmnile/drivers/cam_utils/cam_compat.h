/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Copyright (c) 2014-2020, The Linux Foundation. All rights reserved.
 */

#ifndef _CAM_COMPAT_H_
#define _CAM_COMPAT_H_

#include <linux/version.h>
#include <linux/platform_device.h>
#include <linux/component.h>

int camera_component_match_add_drivers(struct device *master_dev,
	struct component_match **match_list);

#endif /* _CAM_COMPAT_H_ */
