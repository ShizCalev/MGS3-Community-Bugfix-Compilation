// ReSharper disable CppUseAuto
// ReSharper disable IdentifierTypo
#include "stdafx.h"
#include "bugfix_mod_checks.hpp"

#include "common.hpp"
#include "logging.hpp"
#include "version.h"


namespace
{
    constexpr size_t ConstStrLen(const char* str)
    {
        size_t len = 0;

        while (str[len] != '\0')
        {
            ++len;
        }

        return len;
    }

    constexpr bool IsHex(char c)
    {
        return
            (c >= '0' && c <= '9') ||
            (c >= 'a' && c <= 'f') ||
            (c >= 'A' && c <= 'F');
    }

    constexpr bool IsValidSHA1(const char* str)
    {
        if (!str || ConstStrLen(str) != 40)
        {
            return false;
        }

        for (size_t i = 0; i < 40; ++i)
        {
            if (!IsHex(str[i]))
            {
                return false;
            }
        }

        return true;
    }


    //Community Bugfix hashes
    constexpr const char* CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "f6402f8550b38bec5a7f87c1cd1b47215ee68a44";
    constexpr const char* CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "f6402f8550b38bec5a7f87c1cd1b47215ee68a44";
    constexpr const char* CBFC_2x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "1d946a723f63406bba766ee920cad26d78456c1f";
    constexpr const char* CBFC_4x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "9e261951483a5e65e7e5e2ce25c44b06fe91c7c1";

    constexpr const char* CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_SHA1 = "794b85ace976f091704847280578dbe2bc907012";
    constexpr const char* CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_SHA1 = "74bddbddbe4b0cba10b4434edfc326b53809cce6";

    constexpr const char* CBFC_BASE_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1 = "88135145c077132fb9828d5812619fa62b35bb28";


    constexpr const char* CBFC_BASE_OVR_US_oum_allbody_col00_CTXR_SHA1 = "dab605338d0b7f4d01fb64c92fa1b1e039e1ae57";
    constexpr const char* CBFC_2x_OVR_US_oum_allbody_col00_CTXR_SHA1 = "487b19686e70d086b2c0111a5008bb08ba5078bb"; 
    constexpr const char* CBFC_4x_OVR_US_oum_allbody_col00_CTXR_SHA1 = "a532b11ee1c019f3576b5e78bf474ec6004538d4";



    //Third party mods
    constexpr const char* LIQMIX_SLOP_4X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "d31e950cbad76bdf333646e99980a8212f9caa08";
    constexpr const char* LIQMIX_SLOP_2X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "1fa54a4b8b13915360dbb31bf43d820f85b7b1d7";

    constexpr const char* LIQMIX_SLOP_2X_s053a_sky_load_n_CTXR_SHA1 = "6030eeb3ab7e28a28b1ea2a5d98d841d7d685b09";
    constexpr const char* LIQMIX_SLOP_4X_s053a_sky_load_n_CTXR_SHA1 = "a2ea4280c0be2a30f1aa3b33be6a21b62695d6fd";


    constexpr const char* SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1 = "d28087fec6a3d979ef9def837aa0b9db57e795b7";




    static_assert(IsValidSHA1(CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_2x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_4x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_SHA1));

    static_assert(IsValidSHA1(CBFC_BASE_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1));
    
    static_assert(IsValidSHA1(CBFC_BASE_OVR_US_oum_allbody_col00_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_2x_OVR_US_oum_allbody_col00_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_4x_OVR_US_oum_allbody_col00_CTXR_SHA1));


    static_assert(IsValidSHA1(LIQMIX_SLOP_4X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(LIQMIX_SLOP_2X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(LIQMIX_SLOP_2X_s053a_sky_load_n_CTXR_SHA1));
    static_assert(IsValidSHA1(LIQMIX_SLOP_4X_s053a_sky_load_n_CTXR_SHA1));
    static_assert(IsValidSHA1(SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1));

}


void VerifyInstallation::Check()
{
    spdlog::info("Starting installation verification checks...");
    struct FileHashResult
    {
        std::filesystem::path path;
        bool exists = false;
        std::optional<std::array<std::uint8_t, 20>> sha1;
    };



    const auto openCommunityBugfixPage =
        []()
        {
            if (Util::IsSteamOS())
            {
                spdlog::info("Opening the Community Bugfix Compilation Nexus page is not supported on SteamOS. Please visit the following URL on a different device to download the base package: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files");
                return;
            }
            ShellExecuteA(
                nullptr,
                "open",
                "https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files",
                nullptr,
                nullptr,
                SW_SHOWNORMAL
            );
        };


    auto startHashTask =
        [](const std::filesystem::path& path) -> std::future<FileHashResult>
        {
            return std::async(
                std::launch::async,
                [path]() -> FileHashResult
                {
                    FileHashResult result;
                    result.path = path;
                    result.exists = std::filesystem::exists(path);

                    if (!result.exists)
                    {
                        return result;
                    }

                    result.sha1 = Util::ComputeSHA1Bytes(path);
                    return result;
                });
        };

    spdlog::info("Calculating file hashes for installation verification...");
    const std::filesystem::path CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_PATH =    sExePath / "hqtex"    / "flatlist" / "_win" / "eve_item_sunglasses_sub_ovl_alp.bmp.ctxr";
    const std::filesystem::path CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_PATH =          sExePath / "textures" / "flatlist" / "_win" / "eve_item_sunglasses_sub_ovl_alp.bmp.ctxr";
    const std::filesystem::path CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_PATH =        sExePath / "textures" / "flatlist" / "ovr_stm" / "_win" / "eve_item_sunglasses_sub_ovl_alp.bmp.ctxr";

    const std::filesystem::path CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_PATH =                     sExePath / "hqtex"    / "flatlist" / "_win" / "j01_1.bmp.ctxr";
    const std::filesystem::path CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_PATH =               sExePath / "textures" / "flatlist" / "_win" / "n033a_irona_under.bmp.ctxr";

    const std::filesystem::path CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_PATH =              sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_us" / "_win" / "vva_first_aid_kit_alp_ovl.bmp.ctxr";
    const std::filesystem::path CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_PATH =                     sExePath / "textures" / "flatlist" / "ovr_stm" / "_win" / "vva_first_aid_kit_alp_ovl.bmp.ctxr";
    const std::filesystem::path CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_PATH =                    sExePath / "textures" / "flatlist" / "_win" / "vva_first_aid_kit_alp_ovl.bmp.ctxr";

    const std::filesystem::path LIQMIX_SLOP_s053a_sky_load_n_CTXR_PATH =                                    sExePath / "textures" / "flatlist" / "ovr_stm" / "_win" / "s053a_sky_load_n.bmp.ctxr";

    const std::filesystem::path CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_PATH =              sExePath / "textures" / "flatlist" / "ovr_stm" / "ovr_us" / "_win" / "oum_allbody_col00.bmp.ctxr";
    const std::filesystem::path CBFC_BASE_OVR_STM_oum_allbody_col00_CTXR_PATH =                     sExePath / "textures" / "flatlist" / "ovr_stm" / "_win" / "oum_allbody_col00.bmp.ctxr";
    const std::filesystem::path CBFC_BASE_FLATLIST_oum_allbody_col00_CTXR_PATH =                    sExePath / "textures" / "flatlist" / "_win" / "oum_allbody_col00.bmp.ctxr";




    const auto hashEquals =
        [](const FileHashResult& result, const char* expected) -> bool
        {
            return result.exists && result.sha1.has_value() && Util::SHA1Equals(*result.sha1, expected);
        };

    auto CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE = startHashTask(CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_PATH);
    auto CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE = startHashTask(CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_PATH);
    auto CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE = startHashTask(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_PATH);
    auto CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_FUTURE = startHashTask(CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_PATH);
    auto CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_FUTURE = startHashTask(CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_PATH);
    

    auto CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_FUTURE = startHashTask(CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_PATH);
    auto CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_FUTURE = startHashTask(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_PATH);
    auto CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_FUTURE = startHashTask(CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_PATH);

    
    auto CBFC_BASE_OVR_STM_oum_allbody_col00_CTXR_FUTURE = startHashTask(CBFC_BASE_OVR_STM_oum_allbody_col00_CTXR_PATH);
    auto CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_FUTURE = startHashTask(CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_PATH);
    auto CBFC_BASE_FLATLIST_oum_allbody_col00_CTXR_FUTURE = startHashTask(CBFC_BASE_FLATLIST_oum_allbody_col00_CTXR_PATH);
    auto LIQMIX_SLOP_s053a_sky_load_n_CTXR_FUTURE = startHashTask(LIQMIX_SLOP_s053a_sky_load_n_CTXR_PATH);

    const FileHashResult CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result = CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE.get();   ///hqtex/flatlist/_win/eve_item_sunglasses_sub_ovl_alp.bmp
    const FileHashResult CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result = CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE.get();               ///textures/flatlist/_win/eve_item_sunglasses_sub_ovl_alp.bmp
    const FileHashResult CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result = CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE.get();           ///textures/flatlist/ovr_stm/_win/eve_item_sunglasses_sub_ovl_alp.bmp
    const FileHashResult CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_Result = CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_FUTURE.get();                                     ///hqtex/flatlist/_win/j01_1.bmp
    const FileHashResult CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_Result = CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_FUTURE.get();                         ///textures/flatlist/_win/n033a_irona_under.bmp

    const FileHashResult CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_Result = CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_FUTURE.get();                                     ///textures/flatlist/ovr_stm/_win/vva_first_aid_kit_alp_ovl.bmp
    const FileHashResult CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result = CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_FUTURE.get();                       ///textures/flatlist/ovr_stm/ovr_us/_win/vva_first_aid_kit_alp_ovl.bmp
    const FileHashResult CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_Result = CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_FUTURE.get();                                   ///textures/flatlist/_win/vva_first_aid_kit_alp_ovl.bmp

    const FileHashResult CBFC_BASE_OVR_STM_oum_allbody_col00_CTXR_Result = CBFC_BASE_OVR_STM_oum_allbody_col00_CTXR_FUTURE.get();                                     ///textures/flatlist/ovr_stm/_win/oum_allbody_col00.bmp
    const FileHashResult CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_Result = CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_FUTURE.get();                       ///textures/flatlist/ovr_stm/ovr_us/_win/oum_allbody_col00.bmp
    const FileHashResult CBFC_BASE_FLATLIST_oum_allbody_col00_CTXR_Result = CBFC_BASE_FLATLIST_oum_allbody_col00_CTXR_FUTURE.get();                                   ///textures/flatlist/_win/oum_allbody_col00.bmp
    const FileHashResult LIQMIX_SLOP_s053a_sky_load_n_CTXR_Result = LIQMIX_SLOP_s053a_sky_load_n_CTXR_FUTURE.get();                                                             ///textures/flatlist/ovr_stm/_win/s053a_sky_load_n.bmp

    spdlog::info("File hash calculations completed, starting verification...");

    // ------------------------------------------------------
    // MGS3: Verify Afevis Bugfix Collection (base) installation
    // ------------------------------------------------------
    spdlog::info("Verifying Community Bugfix Compilation base installation...");
    if (!CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result.exists || !hashEquals(CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1))
    {
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base) Missing ! -------------------");
        spdlog::warn("Community Bugfix Compilation installation issue detected, base package is NOT found.");
        spdlog::warn("This can occur if Steam has verified integrity and damaged your mod files, or if the Base Bugfix Compilation zip wasn't installed.");
        spdlog::warn("The base package is required for proper functionality, even when 2x & 4x packages are installed.");
        spdlog::warn("Please install the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base) Missing ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Community Bugfix Compilation installation issue detected, base package is NOT found.\n"
            "\n"
            "This can occur if Steam has verified integrity and damaged your mod files, or if the Base Bugfix Compilation zip wasn't installed.\n"
            "\n"
            "The base package is required for proper functionality, even when 2x & 4x packages are installed.\n"
            "Please install the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to download the base package?\n"
            "\n"
            "(GitHub releases link also available on the Nexus page.)",
            "Community Bugfix Compilation (Base) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }


    spdlog::info("Community Bugfix Compilation base installation verified, now checking for high resolution DLC fixes...");
    // ------------------------------------------------------
    // MGS3: Verify Afevis Bugfix Collection (base - hqtex)
    // ------------------------------------------------------
    if (!CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result.exists)
    {
        spdlog::info("Community Bugfix Compilation base installation high resolution (hqtex) DLC not found, DLC was likely uninstalled after installation. Skipping hash check...");
    }
    else if (!hashEquals(CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1))
    {
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base - HQTex) Missing ! -------------------");
        spdlog::warn("Community Bugfix Compilation installation issue detected, base installation high resolution (hqtex) fixes are missing.");
        spdlog::warn("This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the official high resolution DLC after installing the Community Bugfix Compilation.");
        spdlog::warn("Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base) Missing ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Community Bugfix Compilation installation issue detected, base installation high resolution (hqtex) fixes are missing.\n"
            "\n"
            "This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the official high resolution DLC after installing the Community Bugfix Compilation.\n"
            "\n"
            "Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to download the base package?\n"
            "\n"
            "(GitHub releases link also available on the Nexus page.)",
            "Community Bugfix Compilation (Base - HQTex) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }

    spdlog::info("Community Bugfix Compilation high resolution (hqtex) fixes verified, now checking for standard JPN DLC specific fixes...");
    // ------------------------------------------------------
    // MGS3: Verify Afevis Bugfix Collection (base - jp dlc)
    // ------------------------------------------------------
    if (!CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_Result.exists)
    {
        spdlog::info("Community Bugfix Compilation base installation JPN DLC not found, DLC was likely uninstalled after installation. Skipping hash check...");
    }
    else if (!hashEquals(CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_Result, CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_SHA1))
    {
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base - JPN DLC) Missing ! -------------------");
        spdlog::warn("Community Bugfix Compilation installation issue detected, base installation (JPN DLC) fixes are missing.");
        spdlog::warn("This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the Japanese Language DLC after installing the Community Bugfix Compilation.");
        spdlog::warn("Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base - JPN DLC) Missing ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Community Bugfix Compilation installation issue detected, base installation (JPN DLC) fixes are missing.\n"
            "\n"
            "This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the Japanese Language DLC after installing the Community Bugfix Compilation.\n"
            "\n"
            "Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to download the base package?\n"
            "\n"
            "(GitHub releases link also available on the Nexus page.)",
            "Community Bugfix Compilation (Base - JPN DLC) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }

    spdlog::info("Community Bugfix Compilation Japan DLC fixes verified, now checking for high resolution (hqtex) JPN DLC specific fixes...");
    // ------------------------------------------------------
    // MGS3: Verify Afevis Bugfix Collection (base - hqtex - jp dlc)
    // ------------------------------------------------------
    if (!CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_Result.exists)
    {
        spdlog::info("Community Bugfix Compilation base installation JPN DLC not found, DLC was likely uninstalled after installation. Skipping hash check...");
    }
    else if (!hashEquals(CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_Result, CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_SHA1))
    {
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base - HQTex - JPN DLC) Missing ! -------------------");
        spdlog::warn("Community Bugfix Compilation installation issue detected, base installation high resolution (hqtex - JPN DLC) fixes are missing.");
        spdlog::warn("This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the official high resolution DLC after installing the Community Bugfix Compilation.");
        spdlog::warn("Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base - HQTex - JPN DLC) Missing ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Community Bugfix Compilation installation issue detected, base installation high resolution (hqtex - JPN DLC) fixes are missing.\n"
            "\n"
            "This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the official high resolution DLC after installing the Community Bugfix Compilation.\n"
            "\n"
            "Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to download the base package?\n"
            "\n"
            "(GitHub releases link also available on the Nexus page.)",
            "Community Bugfix Compilation (Base - HQTex - JPN DLC) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }




    spdlog::info("Community Bugfix Compilation JPN DLC specific fixes verified.");

    bool b_Detected_Upscaled_Textures = CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result.exists;
    bool b_Liqmix_s053a_sky_load_n_Found = LIQMIX_SLOP_s053a_sky_load_n_CTXR_Result.exists && (hashEquals(LIQMIX_SLOP_s053a_sky_load_n_CTXR_Result, LIQMIX_SLOP_2X_s053a_sky_load_n_CTXR_SHA1) 
                                                                                            || hashEquals(LIQMIX_SLOP_s053a_sky_load_n_CTXR_Result, LIQMIX_SLOP_4X_s053a_sky_load_n_CTXR_SHA1));
    bool is_4x_pack = false;
    bool is_2x_pack = false;

    if (!b_Detected_Upscaled_Textures && !b_Liqmix_s053a_sky_load_n_Found)
    {
        spdlog::info("No upscaled texture pack detected.");
    }
    else
    {
        spdlog::info("Upscaled texture pack detected. Verifying compatibility.");


        // ------------------------------------------------------
        // MGS3: Check if liqmix AI slop packs are installed
        // ------------------------------------------------------
        const bool isLiqMixPack = hashEquals(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, LIQMIX_SLOP_4X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1) ||
                                  hashEquals(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, LIQMIX_SLOP_2X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1);
        if (b_Liqmix_s053a_sky_load_n_Found || isLiqMixPack)
        {
            std::string LiqMix_Message = (b_Liqmix_s053a_sky_load_n_Found && !isLiqMixPack) ? "Leftover files from LiqMix's AI Slop Upscaled texture pack have been detected." : "LiqMix's AI Slop Upscaled texture pack has been detected.";
            spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");
            spdlog::warn(LiqMix_Message);
            spdlog::warn("LiqMix's AI Slop Upscaled texture pack is VERY out of date and has been replaced by the MGS3 Community Bugfix Compilation's Upscaled Texture Addon packs, which also includes all the texture fixes from the CBFC base.");
            spdlog::warn("Please uninstall LiqMix's AI Slop Upscaled texture pack to ensure proper game functionality.");
            spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download our upscaled texture package.");
            spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
            spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");

            if (int result = MessageBoxA(
                nullptr,
                (   LiqMix_Message + "\n"
                "\n"
                "LiqMix's AI Slop texture pack is VERY out of date and has been replaced by the Community Bugfix Compilation's Upscaled Texture Addon packs, which also includes all the texture fixes from the CBFC base.\n"
                "\n"
                "Please uninstall LiqMix's AI Slop Upscaled texture pack to ensure proper game functionality.\n"
                "\n"
                "Would you like to open the Community Bugfix Nexus download page now to download the CBFC Upscaled Texture Addon pack?\n"
                "\n"
                "(GitHub releases link also available on the Nexus page.)").c_str(),
                "Community Bugfix Compilation (CBFC) - Mod Compatibility Issue",
                MB_ICONWARNING | MB_YESNO);
                result == IDYES)
            {
                openCommunityBugfixPage();
            }

            return;
        }


        spdlog::info("Upscaled texture pack is confirmed to not be outdated LiqMix's AI Slop pack, verifying upscaled addon version matches against base version...");
        is_4x_pack = hashEquals(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, CBFC_4x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1);
        is_2x_pack = hashEquals(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, CBFC_2x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1);
        if (!is_4x_pack && !is_2x_pack)
        {
            spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Addon) Installation Issue ! -------------------");
            spdlog::warn("Community Bugfix Compilation Upscaled Texture Addon installation issue detected.");
            spdlog::warn("Unexpected SHA1 hash for ovr_stm/_win/eve_item_sunglasses_sub_ovl_alp.bmp.ctxr.");
            spdlog::warn("This usually indicates that an outdated version of the Upscaled Texture Addon was installed after a newer base version.");
            spdlog::warn("Please ensure that the Upscaled Texture Addon's zip file matches the same version number as your base download zip.");
            spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to redownload the Upscaled Addon.");
            spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
            spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Addon) Installation Issue ! -------------------");

            if (int result = MessageBoxA(
                nullptr,
                "Community Bugfix Compilation Upscaled Texture Addon installation issue detected.\n"
                "\n"
                "Unexpected SHA1 hash for ovr_stm/_win/eve_item_sunglasses_sub_ovl_alp.bmp.ctxr.\n"
                "This usually indicates that an outdated version of the Upscaled Texture Addon was installed after a newer base version.\n"
                "\n"
                "Please ensure that the Upscaled Texture Addon's zip file matches the same version number as your base download zip.\n"
                "\n"
                "Would you like to open the Community Bugfix Nexus download page now to redownload the CBFC Upscaled Addon?\n"
                "\n"
                "(GitHub releases link also available on the Nexus page.)",
                "Community Bugfix Compilation (Upscaled Addon) Installation Issue",
                MB_ICONWARNING | MB_YESNO);
            result == IDYES)
            {
                openCommunityBugfixPage();
            }
        
            return;
        }
        spdlog::info("Upscaled texture pack installation verified. Detected " + std::string(is_4x_pack ? "4x" : is_2x_pack ? "2x" : "unknown") + " upscaled texture pack.");

    }

    spdlog::info("Checking for specific incompatible mod: Outdated Red Cross Restoration mod...");
    if ((CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result.exists && hashEquals(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result, SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1))
        || (CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_Result.exists && hashEquals(CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_Result, SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1))
        || (CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_Result.exists && hashEquals(CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_Result, SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1)))
    {

        spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");
        spdlog::warn("Outdated mod detected: Springas's Red Cross Restoration.");
        spdlog::warn("Springas's Red Cross Restoration mod has been replaced by the Community Bugfix Compilation's re-imported higher-quality PS2 NPOT textures, which also restore the original red crosses.");
        spdlog::warn("Please uninstall Springas's Red Cross Restoration mod to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to redownload the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Outdated mod detected: Springas's Red Cross Restoration.\n"
            "\n"
            "Springas's Red Cross Restoration mod has been replaced by the Community Bugfix Compilation's re-imported higher-quality PS2 NPOT textures, which also restore the original red crosses.\n"
            "\n"
            "Please uninstall Springas's Red Cross Restoration mod to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to redownload the base package?\n"
            "\n"
            "(GitHub releases link also available on the Nexus page.)",
            "Community Bugfix Compilation (CBFC) - Mod Compatibility Issue",
            MB_ICONWARNING | MB_YESNO);
            result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }
    
    spdlog::info("No incompatible mods detected, now checking for potential addon pack installation issues...");


    if (CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_Result.exists)
    {
        if (is_2x_pack || is_4x_pack)
        {
            if (hashEquals(CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_Result, CBFC_BASE_OVR_US_oum_allbody_col00_CTXR_SHA1))
            {
                const char* pack = is_2x_pack ? "2x" : "4x";

                spdlog::warn("------------------- ! Community Bugfix Compilation ({} Upscaled Addon) Installation Issue ! -------------------", pack);
                spdlog::warn("Community Bugfix Compilation {} installation issue detected.", pack);
                spdlog::warn("The base package was installed or loaded after the {} Upscaled Addon.", pack);
                spdlog::warn("The {} Upscaled Addon must be installed or loaded AFTER the base package.", pack);
                spdlog::warn("Please reinstall the {} Upscaled Addon to ensure correct behavior.", pack);
                spdlog::warn("If you are using a mod manager, make sure the {} Upscaled Addon is loaded AFTER the base package.", pack);
                spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to redownload the {} Upscaled Addon.", pack);
                spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
                spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Addon) Installation Issue ! -------------------");
                
                std::string msg =
                    "Community Bugfix Compilation installation issue detected.\n"
                    "\n"
                    "The base package was installed or loaded after the " + std::string(pack) + " Upscaled Addon.\n"
                    "\n"
                    "The " + std::string(pack) + " Upscaled Addon must be installed or loaded AFTER the base package.\n"
                    "\n"
                    "Please reinstall the " + std::string(pack) + " Upscaled Addon to ensure correct behavior.\n"
                    "If using a mod manager, make sure the " + std::string(pack) + " Upscaled Addon is loaded AFTER the base package.\n"
                    "\n"
                    "Open the Nexus download page to redownload the " + std::string(pack) + " Upscaled Addon?\n"
                                                                                            "\n"
                    "(GitHub releases link also available on the Nexus page.)";
                
                std::string title = "Community Bugfix Compilation (" + std::string(pack) + " Upscaled) Installation Issue";
                
                if (int result = MessageBoxA(nullptr, msg.c_str(), title.c_str(), MB_ICONWARNING | MB_YESNO);
                    result == IDYES)
                {
                    openCommunityBugfixPage();
                }
                
                return;
            }

            bool vaa_matches_4x = hashEquals(CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_Result, CBFC_4x_OVR_US_oum_allbody_col00_CTXR_SHA1);
            bool vaa_matches_2x = hashEquals(CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_Result, CBFC_2x_OVR_US_oum_allbody_col00_CTXR_SHA1);

            if (!vaa_matches_4x && !vaa_matches_2x)
            {
                spdlog::warn("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/oum_allbody_col00.bmp.ctxr unknown hash, but upscaled texture pack is installed. This may be caused by a conflicting mod that replaced the texture with an unknown version. Please check your installed mods for conflicts if you are experiencing issues.");
            }
            else if ((vaa_matches_2x && is_4x_pack) || (vaa_matches_4x && is_2x_pack))
            {
                spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Addon) Installation Issue ! -------------------");
                spdlog::warn("Community Bugfix Compilation {} installation issue detected.", is_4x_pack ? "4x" : "2x");
                spdlog::warn("Leftover textures from a previous installation of the {} Upscaled Addon detected.", is_4x_pack ? "2x" : "4x");
                spdlog::warn("Please reinstall the {} Upscaled Addon to ensure correct behavior.", is_4x_pack ? "4x" : "2x");

                std::string msg =
                    "Community Bugfix Compilation installation issue detected.\n"
                    "\n"
                    "Leftover textures from a previous installation of the " + std::string(is_4x_pack ? "2x" : "4x") + " Upscaled Addon detected.\n"
                    "\n"
                    "Please reinstall the " + std::string(is_4x_pack ? "4x" : "2x") + " Upscaled Addon to ensure correct behavior.\n"
                    "\n"
                    "Open the Nexus download page to redownload the " + std::string(is_4x_pack ? "4x" : "2x") + " Upscaled Addon?\n"
                                                                                                                "\n"
                    "(GitHub releases link also available on the Nexus page.)";
                if (int result = MessageBoxA(nullptr, msg.c_str(), "Community Bugfix Compilation (Upscaled Addon) Installation Issue", MB_ICONWARNING | MB_YESNO);
                    result == IDYES)
                {
                    openCommunityBugfixPage();
                }
                return;
            }
            else
            {
                spdlog::info("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/oum_allbody_col00.bmp.ctxr MATCHES expected hash for {} upscaled texture pack.", is_4x_pack ? "4x" : "2x");
            }

        }
        else if (!hashEquals(CBFC_BASE_OVR_STM_OVR_US_oum_allbody_col00_CTXR_Result, CBFC_BASE_OVR_US_oum_allbody_col00_CTXR_SHA1))
        {
            spdlog::warn("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/oum_allbody_col00.bmp.ctxr unknown hash. This may be caused by a conflicting mod that replaced the texture with an unknown version. Please check your installed mods for conflicts if you are experiencing issues.");
        }
        else
        {
            spdlog::info("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/oum_allbody_col00.bmp.ctxr MATCHES expected base package hash.");
        }


    }
    else
    {
        spdlog::warn("ovr_stm/ovr_us/oum_allbody_col00.bmp.ctxr not found, unable to perform installation verification check for CBFC fixes.");
    }



}

