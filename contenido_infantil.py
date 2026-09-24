"""Base de contenido educativo bilingüe (español / inglés) para niños de 2 a 5 años.

Cada tema tiene una lista de elementos con la palabra en ambos idiomas, una
frase de refuerzo y un prompt (en inglés) para generar o buscar la imagen.
Tener ambos idiomas aquí permite el doblaje exacto: el video en inglés usa
las mismas escenas, imágenes y estructura que el video en español.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Elemento:
    clave: str
    es: str
    art_es: str
    en: str
    art_en: str
    extra_es: str
    extra_en: str
    prompt: str  # descripción visual en inglés (para IA o búsqueda de stock)
    color: tuple[int, int, int] | None = None  # para ilustraciones procedurales
    forma: str | None = None  # para ilustraciones procedurales de formas
    cantidad: int | None = None  # para números

    def palabra(self, idioma: str) -> str:
        return self.es if idioma == "es" else self.en

    def articulo(self, idioma: str) -> str:
        return self.art_es if idioma == "es" else self.art_en

    def extra(self, idioma: str) -> str:
        return self.extra_es if idioma == "es" else self.extra_en

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Tema:
    clave: str
    categoria: str
    tipo: str  # animal | objeto | color | numero | forma | emocion | saludo
    titulo_es: str
    titulo_en: str
    gancho_es: str
    gancho_en: str
    items: list[Elemento] = field(default_factory=list)
    palabras_clave: list[str] = field(default_factory=list)
    gancho_item: str = ""  # clave del elemento que responde al gancho del Short

    def titulo(self, idioma: str) -> str:
        return self.titulo_es if idioma == "es" else self.titulo_en

    def gancho(self, idioma: str) -> str:
        return self.gancho_es if idioma == "es" else self.gancho_en


def _e(clave, es, art_es, en, art_en, extra_es, extra_en, prompt, **kw) -> Elemento:
    return Elemento(clave, es, art_es, en, art_en, extra_es, extra_en, prompt, **kw)


TEMAS: dict[str, Tema] = {}


def _registrar(t: Tema) -> None:
    TEMAS[t.clave] = t


# ---------------------------------------------------------------- ANIMALES
_registrar(Tema(
    "animales_granja", "animales", "animal",
    "Los animales de la granja", "Farm animals",
    "¿Sabes qué animal hace ¡muuu!?", "Do you know which animal says moo?",
    [
        _e("vaca", "vaca", "una", "cow", "a", "La vaca hace ¡muuu!", "The cow says moo!", "a happy cute cow in a green meadow"),
        _e("cerdo", "cerdito", "un", "pig", "a", "El cerdito hace ¡oinc, oinc!", "The pig says oink, oink!", "a cute pink pig playing in the mud"),
        _e("gallina", "gallina", "una", "hen", "a", "La gallina hace ¡cocoroco!", "The hen says cluck, cluck!", "a cute hen with little yellow chicks"),
        _e("caballo", "caballo", "un", "horse", "a", "El caballo hace ¡iiiih!", "The horse says neigh!", "a friendly brown horse on a farm"),
        _e("oveja", "oveja", "una", "sheep", "a", "La oveja hace ¡beee!", "The sheep says baa!", "a fluffy white sheep smiling"),
        _e("pato", "pato", "un", "duck", "a", "El pato hace ¡cua, cua!", "The duck says quack, quack!", "a cute yellow duck in a pond"),
    ],
    ["animales", "granja", "sonidos de animales"],
))
_registrar(Tema(
    "animales_selva", "animales", "animal",
    "Los animales de la selva", "Jungle animals",
    "¿Qué animal tiene la trompa más larga?", "Which animal has a very long trunk?",
    [
        _e("leon", "león", "un", "lion", "a", "El león hace ¡grrr!", "The lion says roar!", "a friendly smiling lion cub with a fluffy mane"),
        _e("elefante", "elefante", "un", "elephant", "an", "El elefante tiene una trompa larga.", "The elephant has a long trunk.", "a cute baby elephant spraying water"),
        _e("mono", "mono", "un", "monkey", "a", "El mono come plátanos.", "The monkey eats bananas.", "a happy monkey holding a banana on a tree"),
        _e("jirafa", "jirafa", "una", "giraffe", "a", "La jirafa tiene el cuello largo.", "The giraffe has a long neck.", "a cute tall giraffe eating leaves"),
        _e("tigre", "tigre", "un", "tiger", "a", "El tigre tiene rayas.", "The tiger has stripes.", "a cute baby tiger with orange stripes"),
        _e("cebra", "cebra", "una", "zebra", "a", "La cebra es blanca y negra.", "The zebra is black and white.", "a cute zebra with black and white stripes"),
    ],
    ["animales", "selva", "safari"],
))
_registrar(Tema(
    "animales_mar", "animales", "animal",
    "Los animales del mar", "Sea animals",
    "¿Quién vive en el fondo del mar?", "Who lives under the sea?",
    [
        _e("pez", "pez", "un", "fish", "a", "El pez nada, nada, nada.", "The fish swims and swims.", "a colorful cute fish swimming"),
        _e("pulpo", "pulpo", "un", "octopus", "an", "El pulpo tiene ocho brazos.", "The octopus has eight arms.", "a cute purple octopus waving"),
        _e("ballena", "ballena", "una", "whale", "a", "La ballena es muy grande.", "The whale is very big.", "a big friendly blue whale"),
        _e("tortuga", "tortuga", "una", "turtle", "a", "La tortuga nada despacito.", "The turtle swims slowly.", "a cute green sea turtle"),
        _e("delfin", "delfín", "un", "dolphin", "a", "El delfín salta muy alto.", "The dolphin jumps very high.", "a happy dolphin jumping out of the water"),
        _e("cangrejo", "cangrejo", "un", "crab", "a", "El cangrejo camina de lado.", "The crab walks sideways.", "a cute red crab on the sand"),
    ],
    ["animales", "mar", "océano"],
))
_registrar(Tema(
    "mascotas", "animales", "animal",
    "Las mascotas", "Pets",
    "¿Qué mascota dice ¡guau!?", "Which pet says woof?",
    [
        _e("perro", "perro", "un", "dog", "a", "El perro hace ¡guau, guau!", "The dog says woof, woof!", "a cute happy puppy wagging its tail"),
        _e("gato", "gato", "un", "cat", "a", "El gato hace ¡miau!", "The cat says meow!", "a cute fluffy kitten"),
        _e("conejo", "conejo", "un", "rabbit", "a", "El conejo salta, salta.", "The rabbit hops and hops.", "a cute white bunny with long ears"),
        _e("hamster", "hámster", "un", "hamster", "a", "El hámster come semillas.", "The hamster eats seeds.", "a cute hamster with round cheeks"),
        _e("pez_dorado", "pez dorado", "un", "goldfish", "a", "El pez dorado vive en el agua.", "The goldfish lives in water.", "a cute orange goldfish in a round bowl"),
        _e("loro", "loro", "un", "parrot", "a", "El loro repite palabras.", "The parrot repeats words.", "a colorful cute parrot"),
    ],
    ["animales", "mascotas"],
))
_registrar(Tema(
    "insectos", "animales", "animal",
    "Los insectos del jardín", "Garden bugs",
    "¿Qué insecto tiene alas de colores?", "Which bug has colorful wings?",
    [
        _e("mariposa", "mariposa", "una", "butterfly", "a", "La mariposa vuela entre las flores.", "The butterfly flies among the flowers.", "a colorful butterfly on a flower"),
        _e("abeja", "abeja", "una", "bee", "a", "La abeja hace ¡bzzz!", "The bee says buzz!", "a cute friendly bee with a smile"),
        _e("mariquita", "mariquita", "una", "ladybug", "a", "La mariquita tiene puntitos.", "The ladybug has little dots.", "a cute red ladybug with black dots on a leaf"),
        _e("hormiga", "hormiga", "una", "ant", "an", "La hormiga trabaja mucho.", "The ant works very hard.", "a cute little ant carrying a leaf"),
        _e("caracol", "caracol", "un", "snail", "a", "El caracol va muy despacio.", "The snail goes very slowly.", "a cute snail with a spiral shell"),
        _e("grillo", "grillo", "un", "cricket", "a", "El grillo canta de noche.", "The cricket sings at night.", "a cute green cricket playing a violin"),
    ],
    ["animales", "insectos", "jardín"],
))
_registrar(Tema(
    "aves", "animales", "animal",
    "Los pájaros", "Birds",
    "¿Qué pájaro dice ¡uuu, uuu!?", "Which bird says hoo, hoo?",
    [
        _e("buho", "búho", "un", "owl", "an", "El búho hace ¡uuu, uuu!", "The owl says hoo, hoo!", "a cute owl with big eyes on a branch"),
        _e("pinguino", "pingüino", "un", "penguin", "a", "El pingüino camina en el hielo.", "The penguin walks on the ice.", "a cute baby penguin on the ice"),
        _e("flamenco", "flamenco", "un", "flamingo", "a", "El flamenco es rosado.", "The flamingo is pink.", "a cute pink flamingo standing on one leg"),
        _e("aguila", "águila", "un", "eagle", "an", "El águila vuela muy alto.", "The eagle flies very high.", "a friendly cartoon eagle flying in the sky"),
        _e("pajarito", "pajarito", "un", "little bird", "a", "El pajarito canta ¡pío, pío!", "The little bird sings tweet, tweet!", "a cute little blue bird singing"),
        _e("tucan", "tucán", "un", "toucan", "a", "El tucán tiene un pico de colores.", "The toucan has a colorful beak.", "a cute toucan with a big colorful beak"),
    ],
    ["animales", "aves", "pájaros"],
))

# ---------------------------------------------------------------- COLORES
_registrar(Tema(
    "colores", "colores", "color",
    "Los colores", "Colors",
    "¿De qué color es la manzana?", "What color is the apple?",
    [
        _e("rojo", "rojo", "", "red", "", "La manzana es roja.", "The apple is red.", "a shiny red apple", color=(230, 40, 50)),
        _e("azul", "azul", "", "blue", "", "El cielo es azul.", "The sky is blue.", "a blue sky with a blue balloon", color=(30, 110, 230)),
        _e("amarillo", "amarillo", "", "yellow", "", "El sol es amarillo.", "The sun is yellow.", "a smiling yellow sun", color=(255, 210, 0)),
        _e("verde", "verde", "", "green", "", "La rana es verde.", "The frog is green.", "a cute green frog on a leaf", color=(40, 180, 70)),
        _e("naranja", "naranja", "", "orange", "", "La zanahoria es naranja.", "The carrot is orange.", "a cute orange carrot", color=(255, 140, 20)),
        _e("morado", "morado", "", "purple", "", "Las uvas son moradas.", "The grapes are purple.", "a bunch of purple grapes", color=(130, 60, 190)),
        _e("rosa", "rosa", "", "pink", "", "El helado es rosa.", "The ice cream is pink.", "a pink strawberry ice cream cone", color=(255, 120, 180)),
    ],
    ["colores", "aprender colores"],
))

# ---------------------------------------------------------------- NÚMEROS
_NUM_ES = ["uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"]
_NUM_EN = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
_OBJ = [("manzana", "manzanas", "apple", "apples"), ("estrella", "estrellas", "star", "stars"),
        ("globo", "globos", "balloon", "balloons"), ("pelota", "pelotas", "ball", "balls"),
        ("flor", "flores", "flower", "flowers")]


def _numero(n: int) -> Elemento:
    s_es, p_es, s_en, p_en = _OBJ[(n - 1) % len(_OBJ)]
    conteo_es = ", ".join(_NUM_ES[:n])
    conteo_en = ", ".join(_NUM_EN[:n])
    obj_es = s_es if n == 1 else p_es
    obj_en = s_en if n == 1 else p_en
    return _e(
        f"n{n}", _NUM_ES[n - 1], "", _NUM_EN[n - 1], "",
        f"Contamos: {conteo_es}. ¡{_NUM_ES[n - 1].capitalize()} {obj_es}!",
        f"Let's count: {conteo_en}. {_NUM_EN[n - 1].capitalize()} {obj_en}!",
        f"exactly {n} cute {obj_en} in a row, simple counting illustration",
        cantidad=n,
    )


_registrar(Tema(
    "numeros_1_10", "numeros", "numero",
    "Los números del 1 al 10", "Numbers 1 to 10",
    "¿Sabes contar hasta diez?", "Can you count to ten?",
    [_numero(n) for n in range(1, 11)],
    ["números", "contar", "matemáticas"],
))
_registrar(Tema(
    "numeros_1_5", "numeros", "numero",
    "Los números del 1 al 5", "Numbers 1 to 5",
    "¿Cuántas manzanas hay?", "How many apples are there?",
    [_numero(n) for n in range(1, 6)],
    ["números", "contar"],
))

# ---------------------------------------------------------------- FORMAS
_registrar(Tema(
    "formas", "formas", "forma",
    "Las formas", "Shapes",
    "¿Qué forma tiene una pelota?", "What shape is a ball?",
    [
        _e("circulo", "círculo", "un", "circle", "a", "La pelota es un círculo.", "A ball is a circle.", "a big simple circle shape", forma="circulo", color=(255, 89, 94)),
        _e("cuadrado", "cuadrado", "un", "square", "a", "La ventana es un cuadrado.", "A window is a square.", "a big simple square shape", forma="cuadrado", color=(25, 130, 196)),
        _e("triangulo", "triángulo", "un", "triangle", "a", "El techo es un triángulo.", "A roof is a triangle.", "a big simple triangle shape", forma="triangulo", color=(138, 201, 38)),
        _e("estrella", "estrella", "una", "star", "a", "En el cielo brilla una estrella.", "A star shines in the sky.", "a big simple star shape", forma="estrella", color=(255, 202, 58)),
        _e("corazon", "corazón", "un", "heart", "a", "Te quiero con todo mi corazón.", "I love you with all my heart.", "a big simple heart shape", forma="corazon", color=(255, 112, 166)),
        _e("rectangulo", "rectángulo", "un", "rectangle", "a", "La puerta es un rectángulo.", "A door is a rectangle.", "a big simple rectangle shape", forma="rectangulo", color=(106, 76, 147)),
    ],
    ["formas", "figuras geométricas"],
))

# ---------------------------------------------------------------- EMOCIONES
_registrar(Tema(
    "emociones", "emociones", "emocion",
    "Las emociones", "Feelings",
    "¿Cómo te sientes hoy?", "How do you feel today?",
    [
        _e("feliz", "feliz", "", "happy", "", "Cuando juego, estoy feliz.", "When I play, I feel happy.", "a cute child character smiling happily"),
        _e("triste", "triste", "", "sad", "", "Un abrazo ayuda cuando estoy triste.", "A hug helps when I feel sad.", "a cute character looking a little sad, gentle"),
        _e("enojado", "enojado", "", "angry", "", "Si estoy enojado, respiro despacio.", "When I feel angry, I breathe slowly.", "a cute character with a grumpy face, gentle cartoon"),
        _e("sorprendido", "sorprendido", "", "surprised", "", "¡Oh! ¡Una sorpresa!", "Oh! A surprise!", "a cute character with a surprised face and open mouth"),
        _e("cansado", "cansado", "", "tired", "", "Cuando estoy cansado, duermo.", "When I feel tired, I sleep.", "a cute sleepy character yawning"),
        _e("tranquilo", "tranquilo", "", "calm", "", "Respiro y me siento tranquilo.", "I breathe and I feel calm.", "a cute calm character relaxing peacefully"),
    ],
    ["emociones", "sentimientos", "inteligencia emocional"],
))

# ---------------------------------------------------------------- SALUDOS
_registrar(Tema(
    "saludos", "hablar", "saludo",
    "Aprende a decir hola y adiós", "Learn to say hello and goodbye",
    "¿Cómo saludas a tus amigos?", "How do you greet your friends?",
    [
        _e("hola", "hola", "", "hello", "", "Hola, amigo. ¡Hola!", "Hello, friend. Hello!", "a cute character waving hello"),
        _e("adios", "adiós", "", "goodbye", "", "Adiós, ¡hasta luego!", "Goodbye, see you later!", "a cute character waving goodbye"),
        _e("buenos_dias", "buenos días", "", "good morning", "", "Sale el sol: ¡buenos días!", "The sun is up: good morning!", "a cute character waking up with the morning sun"),
        _e("buenas_noches", "buenas noches", "", "good night", "", "Sale la luna: ¡buenas noches!", "The moon is out: good night!", "a cute character in bed under the moon and stars"),
        _e("gracias", "gracias", "", "thank you", "", "Cuando me ayudan, digo gracias.", "When someone helps me, I say thank you.", "a cute character receiving a gift and smiling"),
        _e("por_favor", "por favor", "", "please", "", "Para pedir algo, digo por favor.", "When I ask for something, I say please.", "a cute character politely asking"),
    ],
    ["primeras palabras", "saludos", "aprender a hablar"],
))
_registrar(Tema(
    "primeras_palabras", "hablar", "objeto",
    "Mis primeras palabras", "My first words",
    "¿Puedes decir mamá?", "Can you say mama?",
    [
        _e("mama", "mamá", "", "mom", "", "Mamá me da abrazos.", "Mom gives me hugs.", "a cute cartoon mother hugging her child"),
        _e("papa", "papá", "", "dad", "", "Papá juega conmigo.", "Dad plays with me.", "a cute cartoon father playing with his child"),
        _e("agua", "agua", "", "water", "", "Tengo sed: agua, por favor.", "I'm thirsty: water, please.", "a cute glass of water"),
        _e("pelota", "pelota", "una", "ball", "a", "La pelota rebota.", "The ball bounces.", "a colorful bouncing ball"),
        _e("leche", "leche", "", "milk", "", "La leche está rica.", "Milk is yummy.", "a cute glass of milk"),
        _e("bebe", "bebé", "un", "baby", "a", "El bebé duerme.", "The baby is sleeping.", "a cute sleeping baby"),
    ],
    ["primeras palabras", "aprender a hablar", "vocabulario"],
))

# ---------------------------------------------------------------- OBJETOS / VOCABULARIO
_registrar(Tema(
    "frutas", "comida", "objeto",
    "Las frutas", "Fruits",
    "¿Cuál es tu fruta favorita?", "What is your favorite fruit?",
    [
        _e("manzana", "manzana", "una", "apple", "an", "La manzana es roja y dulce.", "The apple is red and sweet.", "a shiny red apple"),
        _e("platano", "plátano", "un", "banana", "a", "El plátano es amarillo.", "The banana is yellow.", "a yellow banana"),
        _e("fresa", "fresa", "una", "strawberry", "a", "La fresa es pequeña y roja.", "The strawberry is small and red.", "a cute red strawberry"),
        _e("uvas", "uvas", "unas", "grapes", "some", "Las uvas son moradas.", "The grapes are purple.", "a bunch of purple grapes"),
        _e("naranja_f", "naranja", "una", "orange", "an", "La naranja tiene mucho jugo.", "The orange is very juicy.", "a round orange fruit"),
        _e("sandia", "sandía", "una", "watermelon", "a", "La sandía es verde por fuera y roja por dentro.", "The watermelon is green outside and red inside.", "a slice of watermelon"),
    ],
    ["frutas", "comida saludable", "vocabulario"],
))
_registrar(Tema(
    "verduras", "comida", "objeto",
    "Las verduras", "Vegetables",
    "¿Qué verdura le gusta al conejo?", "Which vegetable does the bunny like?",
    [
        _e("zanahoria", "zanahoria", "una", "carrot", "a", "Al conejo le gusta la zanahoria.", "The bunny likes carrots.", "a cute orange carrot"),
        _e("tomate", "tomate", "un", "tomato", "a", "El tomate es redondo y rojo.", "The tomato is round and red.", "a shiny red tomato"),
        _e("brocoli", "brócoli", "un", "broccoli", "", "El brócoli parece un arbolito.", "Broccoli looks like a little tree.", "a cute green broccoli"),
        _e("maiz", "maíz", "un", "corn", "", "El maíz es amarillo.", "Corn is yellow.", "a yellow corn cob"),
        _e("papa_v", "papa", "una", "potato", "a", "Con papas hacemos puré.", "We make mashed potatoes.", "a cute brown potato"),
        _e("lechuga", "lechuga", "una", "lettuce", "", "La lechuga es verde y fresca.", "Lettuce is green and fresh.", "a fresh green lettuce"),
    ],
    ["verduras", "comida saludable"],
))
_registrar(Tema(
    "vehiculos", "vehiculos", "objeto",
    "Los vehículos", "Vehicles",
    "¿Qué vehículo vuela por el cielo?", "Which vehicle flies in the sky?",
    [
        _e("coche", "coche", "un", "car", "a", "El coche hace ¡bip, bip!", "The car goes beep, beep!", "a cute red toy car"),
        _e("autobus", "autobús", "un", "bus", "a", "El autobús lleva a los niños.", "The bus takes the children.", "a cute yellow school bus"),
        _e("tren", "tren", "un", "train", "a", "El tren hace ¡chu, chu!", "The train goes choo, choo!", "a cute colorful toy train"),
        _e("avion", "avión", "un", "airplane", "an", "El avión vuela por el cielo.", "The airplane flies in the sky.", "a cute airplane flying in the clouds"),
        _e("barco", "barco", "un", "boat", "a", "El barco navega en el agua.", "The boat sails on the water.", "a cute sailboat on the sea"),
        _e("bicicleta", "bicicleta", "una", "bicycle", "a", "La bicicleta tiene dos ruedas.", "The bicycle has two wheels.", "a cute colorful bicycle"),
    ],
    ["vehículos", "transportes"],
))
_registrar(Tema(
    "cuerpo", "cuerpo", "objeto",
    "Las partes del cuerpo", "Body parts",
    "¿Dónde está tu nariz?", "Where is your nose?",
    [
        _e("cabeza", "cabeza", "la", "head", "the", "Toco mi cabeza.", "I touch my head.", "a cute child pointing to their head"),
        _e("ojos", "ojos", "los", "eyes", "the", "Con los ojos veo.", "I see with my eyes.", "a cute child with big bright eyes"),
        _e("nariz", "nariz", "la", "nose", "the", "Con la nariz huelo las flores.", "I smell flowers with my nose.", "a cute child smelling a flower"),
        _e("boca", "boca", "la", "mouth", "the", "Con la boca como y canto.", "I eat and sing with my mouth.", "a cute child smiling with an open mouth singing"),
        _e("manos", "manos", "las", "hands", "the", "Con las manos aplaudo.", "I clap with my hands.", "a cute child clapping hands"),
        _e("pies", "pies", "los", "feet", "the", "Con los pies camino.", "I walk with my feet.", "a cute child walking with little feet"),
    ],
    ["cuerpo humano", "partes del cuerpo"],
))
_registrar(Tema(
    "clima", "naturaleza", "objeto",
    "El clima", "The weather",
    "¿Qué sale después de la lluvia?", "What comes after the rain?",
    [
        _e("sol", "sol", "el", "sun", "the", "El sol nos da calor.", "The sun keeps us warm.", "a smiling yellow sun"),
        _e("lluvia", "lluvia", "la", "rain", "the", "Con la lluvia usamos paraguas.", "We use an umbrella in the rain.", "a cute cloud with gentle rain drops"),
        _e("nube", "nube", "una", "cloud", "a", "La nube es blanca y suave.", "The cloud is white and soft.", "a fluffy smiling white cloud"),
        _e("nieve", "nieve", "la", "snow", "the", "Con la nieve hacemos un muñeco.", "We make a snowman with snow.", "a cute snowman in the snow"),
        _e("viento", "viento", "el", "wind", "the", "El viento mueve las hojas.", "The wind moves the leaves.", "leaves blowing in the wind with a kite"),
        _e("arcoiris", "arcoíris", "un", "rainbow", "a", "El arcoíris tiene muchos colores.", "The rainbow has many colors.", "a bright colorful rainbow"),
    ],
    ["clima", "tiempo", "naturaleza"],
))
_registrar(Tema(
    "familia", "hablar", "objeto",
    "Mi familia", "My family",
    "¿Quién te da un abrazo?", "Who gives you a hug?",
    [
        _e("mama_f", "mamá", "", "mom", "", "Mamá me quiere mucho.", "Mom loves me very much.", "a cute cartoon mother smiling"),
        _e("papa_f", "papá", "", "dad", "", "Papá me lleva al parque.", "Dad takes me to the park.", "a cute cartoon father smiling"),
        _e("abuela", "abuela", "", "grandma", "", "La abuela me cuenta cuentos.", "Grandma tells me stories.", "a cute cartoon grandmother reading a book"),
        _e("abuelo", "abuelo", "", "grandpa", "", "El abuelo juega conmigo.", "Grandpa plays with me.", "a cute cartoon grandfather smiling"),
        _e("hermano", "hermano", "", "brother", "", "Mi hermano y yo jugamos.", "My brother and I play together.", "a cute cartoon little brother"),
        _e("hermana", "hermana", "", "sister", "", "Mi hermana canta conmigo.", "My sister sings with me.", "a cute cartoon little sister"),
    ],
    ["familia", "vocabulario"],
))

# Elemento que responde a la pregunta-gancho de cada Short (se muestra al final: retención)
for _clave, _item in {
    "animales_granja": "vaca", "animales_selva": "elefante", "animales_mar": "pulpo", "mascotas": "perro",
    "insectos": "mariposa", "aves": "buho", "colores": "rojo", "numeros_1_10": "n10", "numeros_1_5": "n5",
    "formas": "circulo", "emociones": "feliz", "saludos": "hola", "primeras_palabras": "mama",
    "frutas": "fresa", "verduras": "zanahoria", "vehiculos": "avion", "cuerpo": "nariz", "clima": "arcoiris",
    "familia": "abuela",
}.items():
    TEMAS[_clave].gancho_item = _item

# Emoji de cada elemento: se usa en las ilustraciones procedurales offline
# (fuente Noto Color Emoji, licencia Apache-2.0 / OFL: uso comercial permitido)
EMOJIS = {
    "vaca": "🐄", "cerdo": "🐖", "gallina": "🐔", "caballo": "🐎", "oveja": "🐑", "pato": "🦆",
    "leon": "🦁", "elefante": "🐘", "mono": "🐒", "jirafa": "🦒", "tigre": "🐅", "cebra": "🦓",
    "pez": "🐟", "pulpo": "🐙", "ballena": "🐋", "tortuga": "🐢", "delfin": "🐬", "cangrejo": "🦀",
    "perro": "🐕", "gato": "🐈", "conejo": "🐇", "hamster": "🐹", "pez_dorado": "🐠", "loro": "🦜",
    "mariposa": "🦋", "abeja": "🐝", "mariquita": "🐞", "hormiga": "🐜", "caracol": "🐌", "grillo": "🦗",
    "buho": "🦉", "pinguino": "🐧", "flamenco": "🦩", "aguila": "🦅", "pajarito": "🐦", "tucan": "🦜",
    "rojo": "🍎", "azul": "🎈", "amarillo": "🌞", "verde": "🐸", "naranja": "🥕", "morado": "🍇", "rosa": "🍦",
    "hola": "👋", "adios": "👋", "buenos_dias": "🌅", "buenas_noches": "🌙", "gracias": "🎁", "por_favor": "🙏",
    "mama": "👩", "papa": "👨", "agua": "💧", "pelota": "⚽", "leche": "🥛", "bebe": "👶",
    "manzana": "🍎", "platano": "🍌", "fresa": "🍓", "uvas": "🍇", "naranja_f": "🍊", "sandia": "🍉",
    "zanahoria": "🥕", "tomate": "🍅", "brocoli": "🥦", "maiz": "🌽", "papa_v": "🥔", "lechuga": "🥬",
    "coche": "🚗", "autobus": "🚌", "tren": "🚂", "avion": "✈️", "barco": "⛵", "bicicleta": "🚲",
    "cabeza": "🙂", "ojos": "👀", "nariz": "👃", "boca": "👄", "manos": "👏", "pies": "🦶",
    "sol": "☀️", "lluvia": "🌧️", "nube": "☁️", "nieve": "⛄", "viento": "🌬️", "arcoiris": "🌈",
    "mama_f": "👩", "papa_f": "👨", "abuela": "👵", "abuelo": "👴", "hermano": "👦", "hermana": "👧",
}
_OBJ_EMOJI = {"manzana": "🍎", "estrella": "⭐", "globo": "🎈", "pelota": "⚽", "flor": "🌸"}

# Categorías para series
CATEGORIAS: dict[str, list[str]] = {}
for _t in TEMAS.values():
    CATEGORIAS.setdefault(_t.categoria, []).append(_t.clave)
CATEGORIAS["mixta"] = list(TEMAS.keys())

NOMBRES_CATEGORIAS = {
    "animales": "Animales", "colores": "Colores", "numeros": "Números", "formas": "Formas",
    "emociones": "Emociones", "hablar": "Aprender a hablar", "comida": "Comida",
    "vehiculos": "Vehículos", "cuerpo": "Cuerpo humano", "naturaleza": "Naturaleza",
    "mixta": "Mixta (todos los temas)",
}


def buscar_tema(texto: str) -> Tema | None:
    """Encuentra un tema predefinido a partir de texto libre (ej. 'animales de la granja')."""
    import unicodedata

    def norm(s: str) -> str:
        return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()

    q = norm(texto)
    if texto in TEMAS:
        return TEMAS[texto]
    mejor, puntos = None, 0
    for t in TEMAS.values():
        candidatos = [t.titulo_es, t.titulo_en, t.clave.replace("_", " ")] + t.palabras_clave
        p = 0
        for c in candidatos:
            c = norm(c)
            if c and (c in q or q in c):
                p += len(c)
            p += sum(2 for w in c.split() if len(w) > 3 and w in q.split())
        if p > puntos:
            mejor, puntos = t, p
    return mejor if puntos >= 6 else None


def tema_personalizado(titulo_es: str, palabras_es: list[str], titulo_en: str = "",
                       palabras_en: list[str] | None = None, tipo: str = "objeto") -> Tema:
    """Crea un tema a partir de una lista de palabras del usuario (traduce si hace falta)."""
    from utilidades import slug

    palabras_en = list(palabras_en or [])
    if len(palabras_en) != len(palabras_es) or not titulo_en:
        try:
            from deep_translator import GoogleTranslator

            tr = GoogleTranslator(source="es", target="en")
            if len(palabras_en) != len(palabras_es):
                palabras_en = [tr.translate(p) or p for p in palabras_es]
            titulo_en = titulo_en or tr.translate(titulo_es) or titulo_es
        except Exception:  # noqa: BLE001 - sin conexión: se mantiene el texto original
            palabras_en = palabras_en if len(palabras_en) == len(palabras_es) else list(palabras_es)
            titulo_en = titulo_en or titulo_es
    items = [
        _e(slug(es), es, "", en, "", f"¡{es.capitalize()}!", f"{en.capitalize()}!",
           f"a cute {en}, simple and clear")
        for es, en in zip(palabras_es, palabras_en)
    ]
    return Tema(slug(titulo_es), "personalizado", tipo, titulo_es, titulo_en,
                "¿Sabes qué es esto?", "Do you know what this is?", items,
                [titulo_es.lower()])
