export default async function handler(req, res) {
  if (req.method === 'POST') {
    // Этот код сработает, когда Палпалыч пришлет уведомление об оплате
    console.log("Оплата получена:", req.body);
    
    // Ответ серверу Палпалыча, что всё ок
    res.status(200).send('OK');
  } else {
    res.status(405).send('Method Not Allowed');
  }
}
