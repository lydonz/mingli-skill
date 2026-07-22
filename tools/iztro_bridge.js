#!/usr/bin/env node

/*
 * Minimal stdin/stdout bridge around iztro.  Keeping this bridge tiny lets
 * the Python toolkit use the same proven Ziwei engine as MingLi-Bench.
 */
const { astro } = require("iztro");

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (chunk) => {
  input += chunk;
});
process.stdin.on("end", () => {
  try {
    const payload = JSON.parse(input);
    const convention = payload.ziHourConvention || "benchmark";
    if (!["benchmark", "early", "late"].includes(convention)) {
      throw new Error("ziHourConvention must be benchmark, early, or late");
    }
    // iztro distinguishes early Zi (0) from late Zi (12).  Benchmark mode
    // preserves this project's historic mapping: 23:00 uses late Zi and
    // 00:00 uses early Zi.  Explicit modes make either convention auditable.
    let hourIndex = Math.floor((payload.hour + 1) / 2);
    if (payload.hour === 23) {
      hourIndex = convention === "early" ? 0 : 12;
    } else if (payload.hour === 0 && convention === "late") {
      hourIndex = 12;
    }
    const chart = astro.bySolar(
      `${payload.year}-${payload.month}-${payload.day}`,
      hourIndex,
      payload.gender,
      true,
      "zh-CN"
    );

    const palaces = chart.palaces.map((palace) => ({
      name: palace.name,
      earthlyBranch: palace.earthlyBranch,
      majorStars: palace.majorStars.map((star) => ({
        name: star.name,
        brightness: star.brightness,
        mutagen: star.mutagen,
      })),
      minorStars: palace.minorStars.map((star) => ({
        name: star.name,
        brightness: star.brightness,
        mutagen: star.mutagen,
      })),
      changsheng12: palace.changsheng12,
      decadal: palace.decadal,
      isBodyPalace: palace.isBodyPalace,
    }));

    process.stdout.write(JSON.stringify({
      gender: chart.gender,
      solarDate: chart.solarDate,
      lunarDate: chart.lunarDate,
      chineseDate: chart.chineseDate,
      rawDates: chart.rawDates,
      time: chart.time,
      timeRange: chart.timeRange,
      zodiac: chart.zodiac,
      earthlyBranchOfBodyPalace: chart.earthlyBranchOfBodyPalace,
      earthlyBranchOfSoulPalace: chart.earthlyBranchOfSoulPalace,
      fiveElementsClass: chart.fiveElementsClass,
      ziHourConvention: convention,
      hourIndex,
      palaces,
    }));
  } catch (error) {
    process.stderr.write(`${error.stack || error.message}\n`);
    process.exitCode = 1;
  }
});
