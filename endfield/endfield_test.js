const crypto = require("node:crypto");

/**
 * Node.js version of the Endfield auto check-in script.
 *
 * Run with: `node endfield/endfield_test.js`
 *
 * Recommended: configure secrets with environment variables.
 */

const profiles = [
    {
        // Get this from browser devtools (Network tab) after login.
        cred: process.env.ENDFIELD_CRED || "REPLACE_WITH_CRED",

        // This value is refreshed automatically before check-in.
        token: process.env.ENDFIELD_TOKEN || "",

        // Format example: "3_4760396803_2"
        skGameRole: process.env.ENDFIELD_SK_GAME_ROLE || "REPLACE_WITH_SK_GAME_ROLE",
        platform: process.env.ENDFIELD_PLATFORM || "3",
        vName: process.env.ENDFIELD_VNAME || "1.0.0",
        accountName: process.env.ENDFIELD_ACCOUNT_NAME || "MainAccount"
    }
    // Duplicate this object if you need multiple accounts.
];

const ENABLE_DISCORD_NOTIFY = (process.env.ENABLE_DISCORD_NOTIFY || "true") === "true";
const DISCORD_USER_ID = process.env.DISCORD_USER_ID || "";
const DISCORD_WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL || "";

const URLS = {
    refresh: "https://zonai.skport.com/web/v1/auth/refresh",
    attendance: "https://zonai.skport.com/web/v1/game/endfield/attendance"
};

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function main() {
    const results = [];

    for (const profile of profiles) {
        console.log(`[${profile.accountName}] Checking credentials and performing check-in...`);

        try {
            const newToken = await refreshToken(profile);
            profile.token = newToken;
            console.log(`[${profile.accountName}] Token refreshed successfully.`);

            const claimResult = await autoClaimFunction(profile);
            results.push(claimResult);
        } catch (error) {
            console.error(`[${profile.accountName}] Error: ${error.message}`);
            results.push({
                name: profile.accountName,
                success: false,
                status: "Auth/Refresh Failed",
                rewards: `Please update your 'cred': ${error.message}`
            });
        }

        // Space requests to reduce risk of rate limiting.
        await sleep(1000);
    }

    if (ENABLE_DISCORD_NOTIFY && DISCORD_WEBHOOK_URL) {
        await sendDiscordEmbed(results);
    }
}

async function refreshToken(profile) {
    const { cred, platform, vName } = profile;

    if (!cred || cred === "REPLACE_WITH_CRED") {
        throw new Error("Missing CRED. Set ENDFIELD_CRED or edit the script config.");
    }

    const response = await fetch(URLS.refresh, {
        method: "GET",
        headers: {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            Accept: "application/json, text/plain, */*",
            cred,
            platform,
            vName,
            Origin: "https://game.skport.com",
            Referer: "https://game.skport.com/"
        }
    });

    const json = await safeJson(response);

    if (json.code === 0 && json.data && json.data.token) {
        return json.data.token;
    }

    if (json.code !== 0) {
        throw new Error(`Refresh Failed (Code: ${json.code}, Msg: ${json.message || "Unknown"})`);
    }

    throw new Error("Refresh failed: token missing in API response");
}

async function autoClaimFunction(profile) {
    const { cred, token, skGameRole, platform, vName, accountName } = profile;

    if (!skGameRole || skGameRole === "REPLACE_WITH_SK_GAME_ROLE") {
        throw new Error("Missing skGameRole. Set ENDFIELD_SK_GAME_ROLE or edit the script config.");
    }

    const timestamp = Math.floor(Date.now() / 1000).toString();
    const path = "/web/v1/game/endfield/attendance";
    const body = "";
    const sign = generateSign(path, body, timestamp, token, platform, vName);

    const result = {
        name: accountName,
        success: false,
        status: "",
        rewards: ""
    };

    try {
        const response = await fetch(URLS.attendance, {
            method: "POST",
            headers: {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                Accept: "application/json, text/plain, */*",
                "Content-Type": "application/json",
                "sk-language": "en_US",
                "sk-game-role": skGameRole,
                cred,
                platform,
                vName,
                timestamp,
                sign,
                Origin: "https://game.skport.com",
                Referer: "https://game.skport.com/"
            },
            body
        });

        const json = await safeJson(response);
        console.log(`[${accountName}] API Response Code: ${json.code}`);

        if (json.code === 0) {
            result.success = true;
            result.status = "Check-in Successful";

            if (json.data && Array.isArray(json.data.awardIds)) {
                const awards = json.data.awardIds
                    .map((award) => {
                        const resource = json.data.resourceInfoMap ? json.data.resourceInfoMap[award.id] : null;
                        return resource ? `${resource.name} x${resource.count}` : award.id || "Unknown Item";
                    })
                    .join("\n");
                result.rewards = awards;
            } else {
                result.rewards = "No detailed reward info.";
            }
        } else if (json.code === 10001) {
            result.success = true;
            result.status = "Already Checked In";
            result.rewards = "Nothing to claim";
        } else {
            result.success = false;
            result.status = `Error (Code: ${json.code})`;
            result.rewards = json.message || "Unknown Error";
        }
    } catch (error) {
        result.success = false;
        result.status = "Exception";
        result.rewards = error.message;
        console.error(error);
    }

    return result;
}

function generateSign(path, body, timestamp, token, platform, vName) {
    let str = path + body + timestamp;
    const headerJson = `{"platform":"${platform}","timestamp":"${timestamp}","dId":"","vName":"${vName}"}`;
    str += headerJson;

    const hmacHex = crypto.createHmac("sha256", token).update(str).digest("hex");
    return crypto.createHash("md5").update(hmacHex).digest("hex");
}

async function sendDiscordEmbed(results) {
    const allSuccess = results.every((r) => r.success);
    const hasError = !allSuccess;
    const embedColor = allSuccess ? 5763719 : 15548997;

    const fields = results.map((r) => ({
        name: `Account: ${r.name}`,
        value: `**Status:** ${r.status}\n**Rewards:**\n${r.rewards || "None"}`,
        inline: true
    }));

    const payload = {
        username: "Endfield Assistant",
        avatar_url: "https://pbs.twimg.com/profile_images/1984225639407529984/2_3-HRTS_400x400.jpg",
        embeds: [
            {
                title: "Endfield Daily Check-in Report",
                color: embedColor,
                fields,
                footer: {
                    text: `Time: ${new Date().toLocaleString("en-US", { timeZone: "UTC" })} (UTC)`,
                    icon_url: "https://assets.skport.com/assets/favicon.ico"
                }
            }
        ]
    };

    if (hasError && DISCORD_USER_ID) {
        payload.content = `<@${DISCORD_USER_ID}> Script encountered an error, please check logs.`;
    }

    try {
        await fetch(DISCORD_WEBHOOK_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
    } catch (error) {
        console.error(`Failed to send Discord webhook: ${error.message}`);
    }
}

async function safeJson(response) {
    const text = await response.text();
    try {
        return JSON.parse(text);
    } catch (error) {
        throw new Error(`Invalid JSON response (${response.status}): ${text.slice(0, 300)}`);
    }
}

main().catch((error) => {
    console.error(`Fatal error: ${error.message}`);
    process.exitCode = 1;
});