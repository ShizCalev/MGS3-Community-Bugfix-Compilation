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
    constexpr const char* CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "3083ec9241d5b3baf39a67402b5a472ae2f0f5f5";
    constexpr const char* CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "3083ec9241d5b3baf39a67402b5a472ae2f0f5f5";
    constexpr const char* CBFC_2x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "d18c2a14278675e5fadef4161254887e5630ab65";
    constexpr const char* CBFC_4x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "ad0b69b2b2177a8eb21d07be350ac2d3e55d5c46";

    constexpr const char* CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_SHA1 = "a554251ca743945da71f5ded4c120c4aee74a6b1";
    constexpr const char* CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_SHA1 = "0a52d651f95299470a9a99462c288a7d99824ce4";

    constexpr const char* CBFC_BASE_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1 = "9150a00497c35aa6b1df85491d9493361b566f04";
    constexpr const char* CBFC_2x_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1 = "b912a3b6cf4ebd45d4c5d289e1b8e4b641c837aa"; 
    constexpr const char* CBFC_4x_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1 = "6c59ff02e6158672604410ca11fc81a017415809";

    constexpr const char* LIQMIX_SLOP_4X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "d31e950cbad76bdf333646e99980a8212f9caa08";
    constexpr const char* LIQMIX_SLOP_2X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1 = "1fa54a4b8b13915360dbb31bf43d820f85b7b1d7";

    constexpr const char* SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1 = "d28087fec6a3d979ef9def837aa0b9db57e795b7";


    static_assert(IsValidSHA1(CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_2x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_4x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_BASE_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_2x_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1));
    static_assert(IsValidSHA1(CBFC_4x_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1));
    static_assert(IsValidSHA1(LIQMIX_SLOP_4X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
    static_assert(IsValidSHA1(LIQMIX_SLOP_2X_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1));
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

    const FileHashResult CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result = CBFC_BASE_HQTEX_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE.get();   ///hqtex/flatlist/_win/eve_item_sunglasses_sub_ovl_alp.bmp
    const FileHashResult CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result = CBFC_BASE_FLATLIST_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE.get();               ///textures/flatlist/_win/eve_item_sunglasses_sub_ovl_alp.bmp
    const FileHashResult CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result = CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_FUTURE.get();           ///textures/flatlist/ovr_stm/_win/eve_item_sunglasses_sub_ovl_alp.bmp
    const FileHashResult CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_Result = CBFC_BASE_HQTEX_FLATLIST_WIN_j01_1_JPN_ONLY_CTXR_FUTURE.get();                                     ///hqtex/flatlist/_win/j01_1.bmp
    const FileHashResult CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_Result = CBFC_BASE_FLATLIST_WIN_n033a_irona_under_JPN_ONLY_CTXR_FUTURE.get();                         ///textures/flatlist/_win/n033a_irona_under.bmp
    const FileHashResult CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_Result = CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_FUTURE.get();                                     ///textures/flatlist/ovr_stm/_win/vva_first_aid_kit_alp_ovl.bmp
    const FileHashResult CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result = CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_FUTURE.get();                       ///textures/flatlist/ovr_stm/ovr_us/_win/vva_first_aid_kit_alp_ovl.bmp
    const FileHashResult CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_Result = CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_FUTURE.get();                                   ///textures/flatlist/_win/vva_first_aid_kit_alp_ovl.bmp

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
            "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
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
            "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
            "Community Bugfix Compilation (Base - HQTex) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }


    spdlog::info("Community Bugfix Compilation high resolution DLC fixes verified, now checking for hqtex JPN DLC specific fixes...");
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
            "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
            "Community Bugfix Compilation (Base - HQTex - JPN DLC) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }

    spdlog::info("Community Bugfix Compilation hqtex JPN DLC specific fixes verified, now checking for standard JPN DLC specific fixes...");
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
        spdlog::warn("Community Bugfix Compilation installation issue detected, base installation high resolution (JPN DLC) fixes are missing.");
        spdlog::warn("This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the official high resolution DLC after installing the Community Bugfix Compilation.");
        spdlog::warn("Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation (Base - JPN DLC) Missing ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Community Bugfix Compilation installation issue detected, base installation high resolution (JPN DLC) fixes are missing.\n"
            "\n"
            "This can occur if Steam has verified integrity and damaged your mod files, or if you have reinstalled the official high resolution DLC after installing the Community Bugfix Compilation.\n"
            "\n"
            "Please reinstall the Community Bugfix Compilation -> Base <- package to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to download the base package?\n"
            "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
            "Community Bugfix Compilation (Base - JPN DLC) Missing",
            MB_ICONWARNING | MB_YESNO);
        result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }


    spdlog::info("Community Bugfix Compilation JPN DLC specific fixes verified.");

    bool b_Detected_Upscaled_Textures = CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result.exists;
    bool is_4x_pack = false;
    bool is_2x_pack = false;

    if (!b_Detected_Upscaled_Textures)
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
        if (isLiqMixPack)
        {
            spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");
            spdlog::warn("LiqMix's AI Slop AI Upscaled texture pack has been detected.");
            spdlog::warn("LiqMix's AI Slop texture pack is VERY out of date and has been replaced by the MGS3 Community Bugfix Compilation's Upscaled texture packs, which includes all the texture fixes from the base version.");
            spdlog::warn("Please uninstall LiqMix's AI Slop Upscaled texture pack to ensure proper game functionality.");
            spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to download our upscaled texture package.");
            spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
            spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");

            if (int result = MessageBoxA(
                nullptr,
                "LiqMix's AI Slop AI Upscaled texture pack has been detected.\n"
                "\n"
                "LiqMix's AI Slop texture pack is VERY out of date and has been replaced by the Community Bugfix Compilation's upscaled packs, which includes all the texture fixes from the base version.\n"
                "Please remove LiqMix's AI Slop Upscaled texture pack to ensure proper game functionality.\n"
                "\n"
                "Would you like to open the Community Bugfix Nexus download page now to download the correct package?\n"
                "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
                "Community Bugfix Compilation - Mod Compatibility Issue",
                MB_ICONWARNING | MB_YESNO);
                result == IDYES)
            {
                openCommunityBugfixPage();
            }

            return;
        }
        spdlog::info("Upscaled texture pack is confirmed to not be outdated LiqMix's AI Slop pack, checking for correct installation...");
        is_4x_pack = hashEquals(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, CBFC_4x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1);
        is_2x_pack = hashEquals(CBFC_UPSCALED_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_Result, CBFC_2x_OVRSTM_WIN_eve_item_sunglasses_sub_ovl_alp_CTXR_SHA1);
        if (!is_4x_pack && !is_2x_pack)
        {
            spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Pack) Installation Issue ! -------------------");
            spdlog::warn("Community Bugfix Compilation Upscaled Texture Pack installation issue detected.");
            spdlog::warn("Unable to get the expected SHA1 hash for ovr_stm/_win/eve_item_sunglasses_sub_ovl_alp.bmp.ctxr.");
            spdlog::warn("Please reinstall the Upscaled pack to ensure correct behavior.");
            spdlog::warn("If you are using a mod manager, make sure the Upscaled pack is loaded AFTER the base package.");
            spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to redownload the Upscaled package.");
            spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
            spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Pack) Installation Issue ! -------------------");

            if (int result = MessageBoxA(
                nullptr,
                "Community Bugfix Compilation Upscaled Texture Pack installation issue detected.\n"
                "\n"
                "Unable to get the expected SHA1 hash for ovr_stm/_win/eve_item_sunglasses_sub_ovl_alp.bmp.ctxr. This usually means the base package was installed or loaded after the upscaled pack.\n"
                "The upscaled pack must be installed or loaded AFTER the base package.\n"
                "\n"
                "Please reinstall the Upscaled pack to ensure correct behavior.\n"
                "If you are using a mod manager, make sure the Upscaled pack is loaded AFTER the base package.\n"
                "\n"
                "Would you like to open the Community Bugfix Nexus download page now to redownload the Upscaled package?\n"
                "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
                "Community Bugfix Compilation (Upscaled Pack) Installation Issue",
                MB_ICONWARNING | MB_YESNO);
            result == IDYES)
            {
                openCommunityBugfixPage();
            }
        
            return;
        }
        spdlog::info("Upscaled texture pack installation verified. Detected " + std::string(is_4x_pack ? "4x" : is_2x_pack ? "2x" : "unknown") + " upscaled texture pack.");

    }

    spdlog::info("Checking for specific incompatible mod: Springas's Red Cross Restoration...");
    if ((CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result.exists && hashEquals(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result, SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1))
        || (CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_Result.exists && hashEquals(CBFC_BASE_OVR_STM_vva_first_aid_kit_alp_ovl_CTXR_Result, SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1))
        || (CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_Result.exists && hashEquals(CBFC_BASE_FLATLIST_vva_first_aid_kit_alp_ovl_CTXR_Result, SPRINGAS_MEDKIT_RESTORATION_vaa_first_aid_kit_alp_ovl_CTXR_SHA1)))
    {

        spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");
        spdlog::warn("Springas's Red Cross Restoration mod has been detected.");
        spdlog::warn("Springas's Red Cross Restoration mod has been replaced by the Community Bugfix Compilation's re-imported higher-quality PS2 NPOT textures.");
        spdlog::warn("Please uninstall Springas's Red Cross Restoration mod to ensure proper game functionality.");
        spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to redownload the base package.");
        spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
        spdlog::warn("------------------- ! Community Bugfix Compilation - Mod Compatibility Issue ! -------------------");

        if (int result = MessageBoxA(
            nullptr,
            "Springas's Red Cross Restoration mod has been detected.\n"
            "\n"
            "Springas's Red Cross Restoration mod has been replaced by the Community Bugfix Compilation's re-imported higher-quality PS2 NPOT textures.\n"
            "Please uninstall Springas's Red Cross Restoration mod to ensure proper game functionality.\n"
            "\n"
            "Would you like to open the Community Bugfix Nexus download page now to download the correct package?\n"
            "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
            "Community Bugfix Compilation - Mod Compatibility Issue",
            MB_ICONWARNING | MB_YESNO);
            result == IDYES)
        {
            openCommunityBugfixPage();
        }

        return;
    }
    
    spdlog::info("No incompatible mods detected, now checking for potential addon pack installation issues...");


    if (CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result.exists)
    {
        if (is_2x_pack || is_4x_pack)
        {
            if (hashEquals(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result, CBFC_BASE_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1))
            {
                spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Pack) Installation Issue ! -------------------");
                spdlog::warn("Community Bugfix Compilation Upscaled Texture Pack installation issue detected.");
                spdlog::warn("vva_first_aid_kit_alp.ctxr hash matches base package, but upscaled texture pack is installed.");
                spdlog::warn("This usually means the base package was installed or loaded after the Upscaled pack.");
                spdlog::warn("The Upscaled pack must be installed or loaded AFTER the base package.");
                spdlog::warn("Please reinstall the Upscaled pack to ensure correct behavior.");
                spdlog::warn("If you are using a mod manager, make sure the Upscaled pack is loaded AFTER the base package.");
                spdlog::warn("Please visit our Nexus page at: https://www.nexusmods.com/metalgearsolid3mc/mods/189?tab=files to redownload the Upscaled package.");
                spdlog::warn("Or our GitHub releases page at: https://github.com/ShizCalev/MGS3-Community-Bugfix-Compilation/releases");
                spdlog::warn("------------------- ! Community Bugfix Compilation (Upscaled Pack) Installation Issue ! -------------------");
                if (int result = MessageBoxA(
                    nullptr,
                    "Community Bugfix Compilation Upscaled Texture Pack installation issue detected.\n"
                    "\n"
                    "Unable to get the expected texture hash for vva_first_aid_kit_alp.ctxr in the Upscaled pack. This usually means the base package was installed or loaded after the Upscaled pack.\n"
                    "The Upscaled pack must be installed or loaded AFTER the base package.\n"
                    "\n"
                    "Please reinstall the Upscaled pack to ensure correct behavior.\n"
                    "If you are using a mod manager, make sure the Upscaled pack is loaded AFTER the base package.\n"
                    "\n"
                    "Would you like to open the Community Bugfix Nexus download page now to redownload the upscaled package?\n"
                    "(You can also find a link to our GitHub releases on the Nexus page if preferred.)",
                    "Community Bugfix Compilation (Upscaled) Installation Issue",
                    MB_ICONWARNING | MB_YESNO);
                result == IDYES)
                {
                    openCommunityBugfixPage();
                }
                return;
            }

            bool vaa_matches_4x = hashEquals(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result, CBFC_4x_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1);
            bool vaa_matches_2x = hashEquals(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result, CBFC_2x_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1);

            if (!vaa_matches_4x && !vaa_matches_2x)
            {
                spdlog::warn("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/vva_first_aid_kit_alp_ovl.bmp.ctxr unknown hash, but upscaled texture pack is installed. This may be caused by a conflicting mod that replaced the texture with an unknown version. Please check your installed mods for conflicts if you are experiencing issues.");
            }
            else if ((vaa_matches_2x && is_4x_pack) || (vaa_matches_4x && is_2x_pack))
            {
                spdlog::warn("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/vva_first_aid_kit_alp_ovl.bmp.ctxr hash mismatch with installed upscaled texture pack.");
            }
            else
            {
                spdlog::info("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/vva_first_aid_kit_alp_ovl.bmp.ctxr matches expected hash for installed {} upscaled texture pack.", is_4x_pack ? "4x" : "2x");
            }


        }
        else if (!hashEquals(CBFC_BASE_OVR_STM_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_Result, CBFC_BASE_OVR_US_vva_first_aid_kit_alp_ovl_CTXR_SHA1))
        {
            spdlog::warn("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/vva_first_aid_kit_alp_ovl.bmp.ctxr unknown hash.");
        }
        else
        {
            spdlog::info("Community Bugfix Compilation - flatlist/ovr_stm/ovr_us/vva_first_aid_kit_alp_ovl.bmp.ctxr matches expected base package hash.");
        }



    }
    else
    {
        spdlog::warn("ovr_stm/ovr_us/vva_first_aid_kit_alp_ovl.bmp.ctxr not found, unable to perform installation verification check for this file.");
    }



}

