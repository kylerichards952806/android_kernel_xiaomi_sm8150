# SPDX-License-Identifier: GPL-2.0-only

# auto-detect subdirs
ifneq ($(CONFIG_ARCH_QTI_VM), y)
ifeq ($(CONFIG_ARCH_LAHAINA), y)
include $(srctree)/techpack/video_gen3meta/config/konavid.conf
LINUXINCLUDE    += -include $(srctree)/techpack/video_gen3meta/config/konavidconf.h
endif

# auto-detect subdirs
ifeq ($(CONFIG_ARCH_HOLI), y)
include $(srctree)/techpack/video_gen3meta/config/holivid.conf
endif

ifeq ($(CONFIG_ARCH_HOLI), y)
LINUXINCLUDE    += -include $(srctree)/techpack/video_gen3meta/config/holividconf.h
endif

# auto-detect subdirs
ifeq ($(CONFIG_ARCH_LITO), y)
include $(srctree)/techpack/video_gen3meta/config/litovid.conf
endif

ifeq ($(CONFIG_ARCH_LITO), y)
LINUXINCLUDE    += -include $(srctree)/techpack/video_gen3meta/config/litovidconf.h
endif

# auto-detect subdirs
ifeq ($(CONFIG_ARCH_DIREWOLF), y)
include $(srctree)/techpack/video_gen3meta/config/gen4autovid.conf
endif

ifeq ($(CONFIG_ARCH_DIREWOLF), y)
LINUXINCLUDE    += -include $(srctree)/techpack/video_gen3meta/config/gen4autovidconf.h
endif
endif

# auto-detect subdirs
ifeq (y, $(findstring y, $(CONFIG_ARCH_SM8150) $(CONFIG_ARCH_SA8155) $(CONFIG_ARCH_SA6155) $(CONFIG_ARCH_SA8195)))
include $(srctree)/techpack/video_gen3meta/config/gen3autovid.conf
endif

ifeq (y, $(findstring y, $(CONFIG_ARCH_SM8150) $(CONFIG_ARCH_SA8155) $(CONFIG_ARCH_SA6155) $(CONFIG_ARCH_SA8195)))
LINUXINCLUDE    += -include $(srctree)/techpack/video_gen3meta/config/gen3autovidconf.h
endif

ifeq ($(CONFIG_ARCH_SCUBA), y)
include $(srctree)/techpack/video_gen3meta/config/scubavid.conf
endif

ifeq ($(CONFIG_ARCH_SCUBA), y)
LINUXINCLUDE    += -include $(srctree)/techpack/video_gen3meta/config/scubavidconf.h
endif

LINUXINCLUDE    += -I$(srctree)/techpack/video_gen3meta/include \
                   -I$(srctree)/techpack/video_gen3meta/include/uapi

USERINCLUDE     += -I$(srctree)/techpack/video_gen3meta/include/uapi

obj-y +=msm/
