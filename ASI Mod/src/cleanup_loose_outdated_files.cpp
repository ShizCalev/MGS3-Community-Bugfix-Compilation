// ReSharper disable CppUseAuto
// ReSharper disable IdentifierTypo
#include "stdafx.h"
#include "cleanup_loose_outdated_files.hpp"

#include "common.hpp"
#include "helper.hpp"

//#include "update_hashes_v2_0_2_to_v2_1_2.hpp"

void CleanupOutdatedModfiles::Check()
{
    if (!(eGameType & MGS3))
    {
        return;
    }



    constexpr const char* TEXTURES_FLATLIST_OVR_STM_WIN_CAVE_GREI_WATERTEX_ALP_OVL_REP_BMP_CTXR_SHA1S[] =
    {
        "9874109223ee6e9ff355816c9c03a44d9bc0b7e0", // MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v1.0.0, MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v1.0.1, MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v1.1.0
        "85f387ed978f8634679e84494c6ac5b8fcca8d94", // MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v2.0.0
        "b6d10ec7fbcf7d34b805497e5e3885d8c64f477a", // MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v1.1.0, MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v1.0.0, MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v1.0.1
        "f5f81968f4a582d838c4a1ca67cf0d3bdc53c20b", // MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v2.0.0
        "ad4c90c621915df1cf64e0c3f90c9e60e57ba9c4", // Big Slop (4x)-54-1-0-0-1702854725
        "d170bde99969ff62262dd31631880329202190b1" // Naked Slop (2x)-54-1-0-0-1702855834
    };

    const Util::RemoveFileEntry outdatedFiles[] =
    {
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "_win" / "cave_grei_watertex_alp_ovl_rep.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_WIN_CAVE_GREI_WATERTEX_ALP_OVL_REP_BMP_CTXR_SHA1S }
    };


    Util::RemoveMatchingFiles(outdatedFiles, "outdated mod files");

}

