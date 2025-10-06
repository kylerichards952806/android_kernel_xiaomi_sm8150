#ifndef __UAPI_CAM_HYP_ITF_H__
#define __UAPI_CAM_HYP_ITF_H__

#include <linux/types.h>

struct cam_hyp_intf_hyp_handle_type {
	__u32 fd;
	__u32 handle;
};

#define MSM_CAM_HYP_INTF_IOCTL_MAGIC '^'

#define MSM_CAM_HYP_INTF_IOCTL_GET_HYP_HANDLE\
	_IOWR(MSM_CAM_HYP_INTF_IOCTL_MAGIC, 0,\
	struct cam_hyp_intf_hyp_handle_type)

#define MSM_CAM_HYP_INTF_IOCTL_MAX 0

#endif /*__UAPI_CAM_HYP_ITF_H__*/
