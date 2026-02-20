export default async function handler(req, res) {
  if (req.method === 'POST') {
    const data = req.body; // Данные от Палпалыча
    const botToken = '8240021229:AAHRWYMrJsKABlmWqf8lzWdOfwXeCe64A-8'; // Вставь сюда токен своего бота
    const myChatId = '5996401983'; // Вставь свой ID (можно узнать у @userinfobot)

    // Отправляем уведомление тебе в телеграм, что пришла оплата
    await fetch(`https://api.telegram.org{botToken}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: myChatId,
        text: `💰 Новая оплата!\nСумма: ${data.Amount} ${data.Currency}\nЗаказ №: ${data.OutSum}`
      })
    });

    res.status(200).send('OK');
  } else {
    res.status(405).send('Method Not Allowed');
  }
}
