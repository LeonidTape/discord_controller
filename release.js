require('dotenv').config();

const config = {
  tag_name: "v1.2.3",
  assets: [
    {
      name: "Discord_Bot_Controller.exe",
      browser_download_url: process.env.DOWNLOAD_URL
    }
  ]
};

// Сохраняем JSON в файл или выводим его
const fs = require('fs');
fs.writeFileSync('release.json', JSON.stringify(config, null, 2));
console.log("JSON сгенерирован успешно!");
