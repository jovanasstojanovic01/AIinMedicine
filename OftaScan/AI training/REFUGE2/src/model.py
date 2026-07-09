import torch
import torch.nn as nn
import torch.nn.functional as F

class DoubleConv(nn.Module):
    # Bazični blok arhitekture: dve uzastopne konvolucije 3x3 sa BatchNorm-om i ReLU-om.
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.double_conv = nn.Sequential(
            # bias=False jer BatchNorm već sadrži parametar pristrasnosti (bias), pa bi bio redundantan
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x):
        return self.double_conv(x)

class DownSample(nn.Module):
    # Enkoderski blok (skidanje rezolucije): MaxPool praćen DoubleConv-om.
    def __init__(self, in_channels, out_channels):
        super().__init__()
        self.down = nn.Sequential(
            nn.MaxPool2d(2), # Smanjuje prostorne dimenzije (H i W) napola
            DoubleConv(in_channels, out_channels)
        )

    def forward(self, x):
        return self.down(x)

class UpSample(nn.Module):
    # Dekoderski blok (povećanje rezolucije) sa konkatenacijom skip-veza iz enkodera.
    def __init__(self, in_channels, out_channels):
        super().__init__()
        # ConvTranspose2d duplira prostorne dimenzije i smanjuje broj kanala napola
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = DoubleConv(in_channels, out_channels)

    def forward(self, x1, x2):
        x1 = self.up(x1)
        
        # Dinamičko dopunjavanje (padding) u slučaju da dimenzije enkodera i dekodera odstupaju za piksel
        diffY = x2.size()[2] - x1.size()[2]
        diffX = x2.size()[3] - x1.size()[3]
        x1 = F.pad(x1, [diffX // 2, diffX - diffX // 2, diffY // 2, diffY - diffY // 2])
        
        # Skip connection: spajamo mape odlika niske rezolucije (x1) i visoke rezolucije (x2) po dimenziji kanala
        x = torch.cat([x2, x1], dim=1)
        return self.conv(x)

class RefugeUNet(nn.Module):
    # Glavna UNet arhitektura prilagođena segmentaciji optičkog diska i čašice.
    def __init__(self, in_channels=3, out_channels=2):
        super().__init__()
        # Enkoderska putanja (hvatanje konteksta i semantike)
        self.inc = DoubleConv(in_channels, 64)
        self.down1 = DownSample(64, 128)
        self.down2 = DownSample(128, 256)
        self.down3 = DownSample(256, 512)
        self.down4 = DownSample(512, 1024) # Usko grlo (Bottleneck) sa najgušćim odlikama
        
        # Dekoderska putanja (rekonstrukcija prostorne rezolucije i precizna lokalizacija)
        self.up1 = UpSample(1024, 512)
        self.up2 = UpSample(512, 256)
        self.up3 = UpSample(256, 128)
        self.up4 = UpSample(128, 64)
        
        # Izlazni sloj: 1x1 konvolucija koja projektuje 64 kanala u ciljne klase (disk i čašica)
        self.outc = nn.Conv2d(64, out_channels, kernel_size=1)

    def forward(self, x):
        # Prolaz kroz enkoder uz čuvanje međurezultata za skip veze
        x1 = self.inc(x)
        x2 = self.down1(x1)
        x3 = self.down2(x2)
        x4 = self.down3(x3)
        x5 = self.down4(x4)
        
        # Prolaz kroz dekoder uz spajanje sa sačuvanim prostornim informacijama iz enkodera
        x = self.up1(x5, x4)
        x = self.up2(x, x3)
        x = self.up3(x, x2)
        x = self.up4(x, x1)
        
        logits = self.outc(x)
        return logits

if __name__ == "__main__":
    # Testiranje arhitekture i verifikacija izlaznih dimenzija tenzora
    model = RefugeUNet()
    test_tensor = torch.randn(1, 3, 512, 512) 
    output = model(test_tensor)
    print("Izlazni oblik modela (mora biti [1, 2, 512, 512]):", output.shape)