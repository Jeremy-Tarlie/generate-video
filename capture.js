const puppeteer = require("puppeteer");
const { spawn } = require("child_process");
const path = require("path");
const express = require("express");
const fs = require("fs");
const stream = require("puppeteer-stream");

// Récupère le nom du fichier sans le @ éventuel
const JSON_NAME = process.argv[2].replace(/^@/, "");
const messagesPath = path.resolve(__dirname, "stories", JSON_NAME);
const messagesData = JSON.parse(fs.readFileSync(messagesPath, "utf-8"));
const VIDEO_NAME = messagesData.metadata.name;

// Fonction pour exécuter le script Python
function runPythonScript(name) {
  return new Promise((resolve, reject) => {
    // Utiliser le Python de l'environnement virtuel
    const pythonPath = path.join(__dirname, "venv", "Scripts", "python.exe");
    const pythonProcess = spawn(pythonPath, [name], {
      stdio: "inherit",
    });

    pythonProcess.on("close", (code) => {
      if (code === 0) {
        console.log("✅ Ajout de la voix terminé avec succès !");
        resolve();
      } else {
        reject(
          new Error(`❌ Erreur lors de l'ajout de la voix (code ${code})`)
        );
      }
    });
  });
}

function waitForServerReady(url, timeout = 30000) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    (function check() {
      require("http")
        .get(url, (res) => {
          if (res.statusCode === 200) resolve();
          else if (Date.now() - start > timeout)
            reject(new Error("Timeout serveur"));
          else setTimeout(check, 200);
        })
        .on("error", () => {
          if (Date.now() - start > timeout)
            reject(new Error("Timeout serveur"));
          else setTimeout(check, 200);
        });
    })();
  });
}

(async () => {
  console.log("🔊 Génération des audios en cours...");
  await runPythonScript("generate_audio.py");

  const audioJsonPath = path.resolve(
    __dirname,
    "audios/messages_with_audio.json"
  );
  const audioJson = JSON.parse(fs.readFileSync(audioJsonPath, "utf-8"));
  const DURATION = audioJson.duration_total;
  console.log(DURATION);

  // 1. Serveur Express
  const app = express();
  app.use(express.static(__dirname));
  const server = app.listen(8080, () =>
    console.log("Serveur sur http://127.0.0.1:8080")
  );

  try {
    const file = fs.createWriteStream(__dirname + `/videos/${VIDEO_NAME}.webm`);
    await waitForServerReady("http://127.0.0.1:8080");
    async function startRecording() {
      const browser = await stream.launch({
        executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
        defaultViewport: null, 
      });
      const page = await browser.newPage();
      await page.goto("http://127.0.0.1:8080/index.html");

      // Récupérer la taille de l'élément à capturer
      const rect = await page.evaluate(() => {
        const el = document.querySelector(".backgroundGif");
        const { x, y, width, height } = el.getBoundingClientRect();
        return { x, y, width, height };
      });

      // Ajuster le viewport
      await page.setViewport({
        width: Math.round(rect.width),
        height: Math.round(rect.height),
      });

      // Scroller l'élément en haut à gauche
      await page.evaluate(() => {
        const el = document.querySelector(".backgroundGif");
        el.scrollIntoView({ block: "start", inline: "start" });
      });

      const recorder = await stream.getStream(page, {
        audio: true,
        video: true,
      });
      console.log("recording");

      recorder.pipe(file);
      setTimeout(async () => {
        await recorder.destroy();
        file.close();
        console.log("finished");

        await browser.close();
        server.close();
        process.exit(0);
      }, 1000 * DURATION);

      console.log("✨ Processus terminé avec succès !");
    }
    startRecording();
  } catch (error) {
    console.error("❌ Erreur:", error);
    if (server) server.close();
    process.exit(1);
  }
})();
