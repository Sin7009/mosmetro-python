from pydantic import BaseModel

class Gen204Config(BaseModel):
    default_urls: list[str] = [
        'connectivitycheck.gstatic.com/generate_204',
        'www.gstatic.com/generate_204',
        'connectivitycheck.android.com/generate_204',
        'play.googleapis.com/generate_204',
        'clients1.google.com/generate_204'
    ]
    reliable_urls: list[str] = [
        'www.google.ru/generate_204',
        'www.google.ru/gen_204',
        'google.com/generate_204',
        'gstatic.com/generate_204',
        'maps.google.com/generate_204',
        'mt0.google.com/generate_204',
        'mt1.google.com/generate_204',
        'mt2.google.com/generate_204',
        'mt3.google.com/generate_204',
        'www.google.com/generate_204',
    ]

class Config(BaseModel):
    gen204: Gen204Config = Gen204Config()
    timeout: int = 10
    retries: int = 3

settings = Config()
