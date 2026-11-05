# TIDAL Discord Rich Presence

Windows'ta TIDAL masaüstü uygulamasında çalan parçayı algılar ve Discord profilinde Rich Presence olarak gösterir. Şarkı, sanatçı, albüm ve ilerleme çubuğunu Windows medya oturumundan alır; kapak görseli ve TIDAL bağlantıları için TIDAL kataloğunu arar. İsteğe bağlı olarak Windows bildirim alanında simge olarak çalışır ve Windows oturum açıldığında otomatik başlayabilir.

## Özellikler

- TIDAL masaüstü oynatımını Windows medya denetimlerinden algılama
- Discord'da şarkı adı, sanatçı, albüm ve zaman göstergesi
- TIDAL kataloğundan parça, sanatçı ve albüm eşleştirmesi
- Bildirim alanında simge ve menüden çıkış
- CMD penceresi açmadan çalışma
- İsteğe bağlı Windows oturum açılışında otomatik başlatma
- İkinci örneğin yanlışlıkla açılmasını önleme
- Yerel log dosyalarıyla hata ayıklama

## Gereksinimler

- Windows 10 veya Windows 11
- Python 3.11 veya daha yeni
- Discord masaüstü uygulaması
- TIDAL masaüstü uygulaması ve etkin bir medya oturumu
- Discord Developer Portal'dan bir uygulama kimliği
- TIDAL Developer Portal'dan uygulama kimliği ve gizli anahtar

## Kurulum

PowerShell veya Komut İstemi'nde proje klasörüne geç:

```powershell
cd "$env:USERPROFILE\Documents\tidal-rpc"
```

Bağımlılıkları kur:

```powershell
py -m pip install -r requirements.txt
```

> `winsdk` yerine PyWinRT kullanılır. Böylece Python 3.15'te eski `winsdk` paketinin C++ derlemesi ve Visual Studio gereksinimi oluşmaz.

Örnek ayar dosyasını oluştur ve düzenle:

```powershell
Copy-Item .env.example .env
notepad .env
```

`.env` dosyasında bu değerleri gir:

```dotenv
DISCORD_CLIENT_ID=Discord_Application_ID
TIDAL_CLIENT_ID=TIDAL_Client_ID
TIDAL_CLIENT_SECRET=TIDAL_Client_Secret
TIDAL_COUNTRY_CODE=TR
```

Discord uygulama kimliğini [Discord Developer Portal](https://discord.com/developers/applications) içindeki uygulamanın **General Information** sayfasında bulabilirsin. TIDAL kimlik bilgilerini [TIDAL Developer Portal](https://developer.tidal.com/) üzerinden oluşturduğun uygulamadan al. TIDAL kataloğuna erişim uygulaman için etkin değilse portal üzerinden katalog erişimini etkinleştirmen gerekebilir.

## Çalıştırma

Geliştirme sırasında logları terminalde görmek için:

```powershell
py tidal_rpc.py
```

CMD penceresi olmadan çalıştırmak için:

```powershell
pyw tidal_rpc.py
```

Discord ve TIDAL açıkken bir parça çal. Bildirim alanındaki simge menüsünden **Çıkış** seçerek uygulamayı kapatabilirsin.

## Windows ile otomatik başlatma

Bağımlılıkları kurup `.env` dosyasını doldurduktan sonra PowerShell'de proje klasöründen çalıştır:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_autostart.ps1
```

Uygulama, Windows hesabına giriş yapıldığında gizli konsol olmadan başlar. Başlangıç kısayolunu kaldırmak için:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall_autostart.ps1
```

## Loglar

Loglar Windows'ta şu konuma yazılır:

```text
%LOCALAPPDATA%\TidalRPC\logs\tidal-rpc.log
```

Loglar döndürülür ve üç eski dosyaya kadar saklanır. API erişimi veya Discord bağlantısı çalışmıyorsa bu dosyadaki son hata mesajlarına bak.

## Güvenlik

- `.env` kişisel kimlik bilgilerini içerir ve Git tarafından yok sayılır. Bu dosyayı GitHub'a ekleme.
- Yalnızca `.env.example` dosyasını paylaş.
- Bir Client Secret yanlışlıkla paylaşıldıysa ilgili geliştirici panelinden yenile.
- Discord Application ID gizli anahtar değildir; yine de `.env` ile yerel ayarda tutularak her kullanıcının kendi uygulamasını tanımlaması sağlanır.

## Bilinen sınırlar

- Uygulama Windows ve TIDAL masaüstü medya oturumu için hazırlanmıştır.
- TIDAL araması için TIDAL Developer API erişimi ve uygulama kimlik bilgileri gerekir.
- Kapak URL'si Discord Rich Presence'a gönderilir. Harici görsel URL'lerinin gösterimi Discord istemcisi ve RPC davranışına bağlı olabilir; Discord Developer Portal'da yüklenmiş sabit görseller farklı bir kullanım yoludur.
- TIDAL kataloğunda eşleşme bulunamazsa şarkı ve sanatçı bilgisi Windows medya oturumundan gösterilmeye devam eder, ancak kapak ve TIDAL düğmeleri eklenmez.

## GitHub için önerilen depo açıklaması

> Windows'ta TIDAL'da çalan parçayı algılayıp Discord Rich Presence'ta şarkı bilgisi, ilerleme çubuğu ve TIDAL katalog verilerini gösteren Python uygulaması.

Önerilen konular: `tidal`, `discord-rich-presence`, `python`, `windows`, `music`.

## Atıf

Bu, TIDAL veya Discord tarafından yayımlanmamış bağımsız bir projedir. TIDAL içeriğini kullanırken [TIDAL Developer Guidelines](https://developer.tidal.com/documentation/guidelines-developer-guidelines-2_0) ve API koşullarına uy.
