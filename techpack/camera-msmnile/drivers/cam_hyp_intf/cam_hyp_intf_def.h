#ifndef _CAM_HYP_INTF_DEF_H_
#define _CAM_HYP_INTF_DEF_H_

/**
 * @brief : API to register cam_hyp_intf dev to platform framework.
 * @return struct platform_device pointer on on success, or ERR_PTR() on error.
 */
int cam_hyp_intf_init_module(void);

/**
 * @brief : API to remove cam_hyp_intf dev from platform framework.
 */
void cam_hyp_intf_exit_module(void);

#endif /*_CAM_HYP_INTF_DEF_H_ */