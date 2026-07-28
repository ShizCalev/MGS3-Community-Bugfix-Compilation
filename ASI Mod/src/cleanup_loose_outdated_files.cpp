// ReSharper disable CppUseAuto
// ReSharper disable IdentifierTypo
#include "stdafx.h"
#include "cleanup_loose_outdated_files.hpp"

#include "common.hpp"
#include "helper.hpp"

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

    constexpr const char* TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_REND_BANDANA_BMP_CTXR_SHA1S[] =
    {
        "ebb878f67750abce5bccf311753e9cb26a034a17", // MGS3-Community-Bugfix-Compilation Base v2.0.0
        "4284bc78562f0c21ef1a4570bb0fd12a1d650464", // MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v2.0.0
        "bd4e04557462257977251e0b40ca0465b0dde7cf" // MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v2.0.0
    };

    constexpr const char* TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_ITEM_BANDANNA_BMP_CTXR_SHA1S[] =
    {
        "0ed8ac9949ae521c5a07bb7e838885de6ba13d56", // MGS3-Community-Bugfix-Compilation Base v2.0.0
        "d584fa9aca75bc988164e1a75abf7a56dd1fc5ac", // MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v2.0.0
        "63ef2ae75a10ec4d6b9c3d002e0efde7c886eb02" // MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v2.0.0
    };

    constexpr const char* TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_MGS3_BANDAGE_SHL_BMP_CTXR_SHA1S[] =
    {
        "2c44f2308a4cd14d8bfaf9267ec75025012abd15", // MGS3-Community-Bugfix-Compilation Base v2.0.0
        "a9b6bb3289de30e6fcd2fb566cf46232e13bd68d", // MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v2.0.0
        "ed0416a130708928464af833cc60aa5cf466d275" // MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v2.0.0
    };

    constexpr const char* TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_BANDANA_DEF_BMP_CTXR_SHA1S[] =
    {
        "6bc4ca957b8e53439bd0bafee41980e568b2001b", // MGS3-Community-Bugfix-Compilation Base v2.0.0
        "26ec88f98d6c53027a6705df33174f30df3f7f95", // MGS3-Community-Bugfix-Compilation 2x Upscaled Addon v2.0.0
        "49baa2231691aaa370723b69015d1fa9cdf89598" // MGS3-Community-Bugfix-Compilation 4x Upscaled Addon v2.0.0
    };

    const Util::RemoveFileEntry outdatedFiles[] =
    {

        {sExePath / "textures" / "flatlist" / "ovr_stm" / "_win" / "cave_grei_watertex_alp_ovl_rep.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_WIN_CAVE_GREI_WATERTEX_ALP_OVL_REP_BMP_CTXR_SHA1S },


        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_eu" / "_win" / "sna_mgs3_bandage_shl.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_MGS3_BANDAGE_SHL_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_us" / "_win" / "sna_mgs3_bandage_shl.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_MGS3_BANDAGE_SHL_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_jp" / "_win" / "sna_mgs3_bandage_shl.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_MGS3_BANDAGE_SHL_BMP_CTXR_SHA1S },


        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_jp" / "_win" / "sna_item_bandanna.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_ITEM_BANDANNA_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_eu" / "_win" / "sna_item_bandanna.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_ITEM_BANDANNA_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_us" / "_win" / "sna_item_bandanna.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_ITEM_BANDANNA_BMP_CTXR_SHA1S },

        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_jp" / "_win" / "sna_bandana_def.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_BANDANA_DEF_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_eu" / "_win" / "sna_bandana_def.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_BANDANA_DEF_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_us" / "_win" / "sna_bandana_def.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_SNA_BANDANA_DEF_BMP_CTXR_SHA1S },
        
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_us" / "_win" / "rend_bandana.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_REND_BANDANA_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_eu" / "_win" / "rend_bandana.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_REND_BANDANA_BMP_CTXR_SHA1S },
        {sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_jp" / "_win" / "rend_bandana.bmp.ctxr", TEXTURES_FLATLIST_OVR_STM_OVR_EU_JP_US_WIN_REND_BANDANA_BMP_CTXR_SHA1S },



    };


    Util::RemoveMatchingFiles(outdatedFiles, "outdated mod files");

}

