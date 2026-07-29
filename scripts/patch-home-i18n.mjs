import fs from 'fs'

const path = 'src/i18n.js'
let s = fs.readFileSync(path, 'utf8')

const patches = {
  es: {
    'home.hero.title': 'Mucho más que un hostel.<br />Tu lugar en Valizas.',
    'home.hero.lead':
      'A solo 100 metros del mar, Valizas Hostel Boutique & Suites combina naturaleza, comodidad y experiencias inolvidables. Habitaciones privadas y compartidas, piscina climatizada, desayuno continental casero incluido y la mejor ubicación para descubrir Barra de Valizas.',
    'home.cta.availability': 'Reservar ahora',
    'home.intro.title': 'Tu casa en Valizas',
    'home.intro.text':
      '<p>Hace más de 15 años cumplimos el sueño de crear un hostel frente al mar.</p><p>Nos enamoramos de Valizas por su naturaleza, sus dunas, el océano y su forma de vivir.</p><p>Desde entonces recibimos viajeros de todas partes del mundo ofreciendo una atención personalizada, cálida y cercana.</p><p><strong>No somos una cadena hotelera.</strong></p><p><strong>Somos Leonardo y Rubén.</strong></p><p>Queremos que descubras Valizas como nosotros la vivimos.</p>',
    'home.ico.pool': 'Piscina climatizada',
    'home.ico.beach': '100 metros del mar',
    'home.ico.breakfast': 'Desayuno incluido',
    'home.ico.wifi': 'Wi-Fi gratuito',
    'home.ico.pet': 'Pet Friendly',
    'home.ico.owners': 'Atendido por sus dueños',
    'home.ico.reception': 'Recepción 24 hs (enero)',
    'home.loc.eyebrow': 'Ubicación',
    'home.loc.title': 'En el corazón de Barra de Valizas',
    'home.loc.beach': '100 metros de la playa',
    'home.loc.terminal': '300 metros de la terminal de ómnibus',
    'home.loc.plaza': 'Frente a Plaza Leopoldina Rosa',
    'home.loc.avenue': 'Sobre Avenida Aladino Veiga',
    'home.loc.cabo': '2 horas y media caminando por las dunas hasta Cabo Polonio',
    'home.loc.services':
      'Rodeado de supermercados, panadería, restaurantes, cafeterías, Bora Beer, sushi y todos los servicios.',
    'home.stat.google': 'Valoración Google',
    'home.stat.poolTitle': 'Piscina',
    'home.stat.pool': 'climatizada',
    'home.stat.wifi': 'gratuito',
    'home.stat.reception': 'Recepción (enero)',
    'home.stat.langs': 'en recepción',
    'home.stat.hotwater': 'Agua caliente',
    'home.stat.parkingTitle': 'Parking',
    'home.stat.parking': 'Estacionamiento exclusivo',
    'home.stat.cardsTitle': 'Tarjetas',
    'home.stat.cards': 'Aceptamos todas',
    'exp.title': 'Viví la experiencia Valizas',
    'exp.lead':
      'Más que un alojamiento, te invitamos a vivir unas vacaciones completas. Descubrí nuestras instalaciones, la piscina, los espacios comunes y todo lo que hace único a Valizas Hostel Boutique & Suites.',
    'exp.hint': 'Deslizá para ver pileta, habitaciones, cool living, biblioteca y más',
    'ideal.camps': 'Campamentos Estudiantiles',
    'ideal.campsT':
      'Dormitorios cómodos de 4, 6, 8 y 10 camas con lockers de seguridad, sábanas, Wi-Fi, baños masculinos, femeninos e inclusivos.',
    'ideal.couplesT': 'Habitaciones privadas con balcón, terraza y vistas hacia el mar.',
    'ideal.backpackT':
      'Dormitorios cómodos, cocina totalmente equipada y viajeros de todo el mundo.',
    'ideal.familiesT':
      'Habitaciones familiares, piscina climatizada y playa a solo 100 metros.',
    'ideal.lgbtqT':
      'Un ambiente diverso, respetuoso e inclusivo donde todas las personas son bienvenidas.',
    'page.nosotros.ownerNames': 'Leonardo y Rubén',
    'page.nosotros.owner1': 'Leonardo y Rubén',
    'page.nosotros.owner1s': 'Dueños y anfitriones',
    'page.nosotros.bio':
      'Somos Leonardo y Rubén. Hace más de 15 años creamos este hostel frente al mar para que descubras Valizas como nosotros la vivimos.',
  },
  en: {
    'home.hero.title': 'More than a hostel.<br />Your place in Valizas.',
    'home.hero.lead':
      'Just 100 meters from the sea, Valizas Hostel Boutique & Suites blends nature, comfort and unforgettable experiences. Private and shared rooms, heated pool, homemade continental breakfast included, and the best base to explore Barra de Valizas.',
    'home.cta.availability': 'Book now',
    'home.intro.title': 'Your home in Valizas',
    'home.intro.text':
      '<p>Over 15 years ago we fulfilled the dream of creating a hostel by the sea.</p><p>We fell in love with Valizas for its nature, dunes, ocean and way of life.</p><p>Since then we welcome travelers from all over the world with warm, personal hospitality.</p><p><strong>We are not a hotel chain.</strong></p><p><strong>We are Leonardo and Rubén.</strong></p><p>We want you to discover Valizas the way we live it.</p>',
    'home.ico.pool': 'Heated pool',
    'home.ico.beach': '100 meters from the sea',
    'home.ico.breakfast': 'Breakfast included',
    'home.ico.wifi': 'Free Wi-Fi',
    'home.ico.pet': 'Pet friendly',
    'home.ico.owners': 'Owner-run',
    'home.ico.reception': '24h reception (January)',
    'home.loc.eyebrow': 'Location',
    'home.loc.title': 'In the heart of Barra de Valizas',
    'home.loc.beach': '100 meters from the beach',
    'home.loc.terminal': '300 meters from the bus terminal',
    'home.loc.plaza': 'Facing Plaza Leopoldina Rosa',
    'home.loc.avenue': 'On Aladino Veiga Avenue',
    'home.loc.cabo': 'A 2.5-hour dune walk to Cabo Polonio',
    'home.loc.services':
      'Surrounded by markets, bakery, restaurants, cafés, Bora Beer, sushi and every service you need.',
    'home.stat.google': 'Google rating',
    'home.stat.poolTitle': 'Pool',
    'home.stat.pool': 'heated',
    'home.stat.wifi': 'free',
    'home.stat.reception': 'Reception (January)',
    'home.stat.langs': 'at reception',
    'home.stat.hotwater': 'Hot water',
    'home.stat.parkingTitle': 'Parking',
    'home.stat.parking': 'Guest parking',
    'home.stat.cardsTitle': 'Cards',
    'home.stat.cards': 'All cards accepted',
    'exp.title': 'Live the Valizas experience',
    'exp.lead':
      'More than a place to sleep — a full holiday. Discover our facilities, the pool, common areas and everything that makes Valizas Hostel Boutique & Suites unique.',
    'exp.hint': 'Swipe to see pool, rooms, cool living, library and more',
    'ideal.camps': 'Student camps',
    'ideal.campsT':
      'Comfortable dorms with 4, 6, 8 and 10 beds, lockers, sheets, Wi-Fi, and male, female and inclusive bathrooms.',
    'ideal.couplesT': 'Private rooms with balcony, terrace and sea views.',
    'ideal.backpackT': 'Comfy dorms, fully equipped kitchen and travelers from everywhere.',
    'ideal.familiesT': 'Family rooms, heated pool and beach only 100 meters away.',
    'ideal.lgbtqT': 'A diverse, respectful and inclusive space where everyone is welcome.',
    'page.nosotros.ownerNames': 'Leonardo and Rubén',
    'page.nosotros.owner1': 'Leonardo and Rubén',
    'page.nosotros.owner1s': 'Owners and hosts',
    'page.nosotros.bio':
      'We are Leonardo and Rubén. Over 15 years ago we created this seaside hostel so you can discover Valizas the way we live it.',
  },
  pt: {
    'home.hero.title': 'Muito mais que um hostel.<br />Seu lugar em Valizas.',
    'home.hero.lead':
      'A só 100 metros do mar, o Valizas Hostel Boutique & Suites une natureza, conforto e experiências inesquecíveis. Quartos privados e compartilhados, piscina climatizada, café da manhã continental caseiro incluso e a melhor localização para descobrir Barra de Valizas.',
    'home.cta.availability': 'Reservar agora',
    'home.intro.title': 'Sua casa em Valizas',
    'home.intro.text':
      '<p>Há mais de 15 anos realizamos o sonho de criar um hostel em frente ao mar.</p><p>Nos apaixonamos por Valizas pela natureza, as dunas, o oceano e seu jeito de viver.</p><p>Desde então recebemos viajantes do mundo todo com atenção personalizada, calorosa e próxima.</p><p><strong>Não somos uma rede hoteleira.</strong></p><p><strong>Somos Leonardo e Rubén.</strong></p><p>Queremos que você descubra Valizas como nós a vivemos.</p>',
    'home.ico.pool': 'Piscina climatizada',
    'home.ico.beach': '100 metros do mar',
    'home.ico.breakfast': 'Café incluso',
    'home.ico.wifi': 'Wi-Fi gratuito',
    'home.ico.pet': 'Pet friendly',
    'home.ico.owners': 'Atendido pelos donos',
    'home.ico.reception': 'Recepção 24h (janeiro)',
    'home.loc.eyebrow': 'Localização',
    'home.loc.title': 'No coração de Barra de Valizas',
    'home.loc.beach': '100 metros da praia',
    'home.loc.terminal': '300 metros da terminal de ônibus',
    'home.loc.plaza': 'Em frente à Plaza Leopoldina Rosa',
    'home.loc.avenue': 'Na Avenida Aladino Veiga',
    'home.loc.cabo': '2 horas e meia caminhando pelas dunas até Cabo Polonio',
    'home.loc.services':
      'Cercado de mercados, padaria, restaurantes, cafés, Bora Beer, sushi e todos os serviços.',
    'home.stat.google': 'Avaliação Google',
    'home.stat.poolTitle': 'Piscina',
    'home.stat.pool': 'climatizada',
    'home.stat.wifi': 'gratuito',
    'home.stat.reception': 'Recepção (janeiro)',
    'home.stat.langs': 'na recepção',
    'home.stat.hotwater': 'Água quente',
    'home.stat.parkingTitle': 'Parking',
    'home.stat.parking': 'Estacionamento exclusivo',
    'home.stat.cardsTitle': 'Cartões',
    'home.stat.cards': 'Aceitamos todos',
    'exp.title': 'Viva a experiência Valizas',
    'exp.lead':
      'Mais do que uma cama — umas férias completas. Descubra as instalações, a piscina, os espaços comuns e tudo que torna o Valizas Hostel Boutique & Suites único.',
    'exp.hint': 'Deslize para ver piscina, quartos, cool living, biblioteca e mais',
    'ideal.camps': 'Acampamentos estudantis',
    'ideal.campsT':
      'Dorms confortáveis de 4, 6, 8 e 10 camas com lockers, lençóis, Wi-Fi e banheiros masculinos, femininos e inclusivos.',
    'ideal.couplesT': 'Quartos privados com varanda, terraço e vista para o mar.',
    'ideal.backpackT': 'Dorms confortáveis, cozinha completa e viajantes do mundo todo.',
    'ideal.familiesT': 'Quartos familiares, piscina climatizada e praia a só 100 metros.',
    'ideal.lgbtqT': 'Um ambiente diverso, respeitoso e inclusivo onde todas as pessoas são bem-vindas.',
    'page.nosotros.ownerNames': 'Leonardo e Rubén',
    'page.nosotros.owner1': 'Leonardo e Rubén',
    'page.nosotros.owner1s': 'Donos e anfitriões',
    'page.nosotros.bio':
      'Somos Leonardo e Rubén. Há mais de 15 anos criamos este hostel em frente ao mar para que você descubra Valizas como nós a vivemos.',
  },
}

const galleryKeys = {
  es: {
    'exp.g.pool': 'Piscina',
    'exp.g.poolT': 'Sol, reposeras y agua cristalina en pleno Valizas.',
    'exp.g.heated': 'Piscina climatizada',
    'exp.g.heatedT': 'Para disfrutar también en días frescos.',
    'exp.g.rooms': 'Habitaciones',
    'exp.g.roomsT': 'Privadas y compartidas, listas para descansar.',
    'exp.g.coliving': 'Cool Living',
    'exp.g.colivingT': 'Espacios para conectar, trabajar y compartir.',
    'exp.g.library': 'Biblioteca',
    'exp.g.libraryT': 'Un rincón con libros, tablas y onda de playa.',
    'exp.g.bbq': 'Barbacoa',
    'exp.g.bbqT': 'Asados y encuentros al aire libre.',
    'exp.g.solarium': 'Solárium',
    'exp.g.solariumT': 'Repos, lectura y pileta a unos pasos.',
    'exp.g.bora': 'Bora Beer',
    'exp.g.boraT': 'El resto bar del hostel, sin salir de casa.',
    'exp.g.reception': 'Recepción',
    'exp.g.receptionT': 'Tips de dunas, check-in y buena onda.',
    'exp.g.terrace': 'Terrazas',
    'exp.g.terraceT': 'Pool table y atardeceres.',
    'exp.g.night': 'Hostel de noche',
    'exp.g.nightT': 'La fachada de colores bajo las estrellas.',
    'exp.g.party': 'Ambiente',
    'exp.g.partyT': 'Música, pileta y comunidad.',
    'exp.g.dunas': 'Dunas',
    'exp.g.dunasT': 'Camino a Cabo Polonio desde Valizas.',
    'exp.g.summer': 'Verano',
    'exp.g.summerT': 'Flotadores, sol y ganas de quedarte.',
  },
  en: {
    'exp.g.pool': 'Pool',
    'exp.g.poolT': 'Sun loungers and clear water in Valizas.',
    'exp.g.heated': 'Heated pool',
    'exp.g.heatedT': 'Enjoy it on cooler days too.',
    'exp.g.rooms': 'Rooms',
    'exp.g.roomsT': 'Private and shared, ready to rest.',
    'exp.g.coliving': 'Cool Living',
    'exp.g.colivingT': 'Spaces to connect, work and share.',
    'exp.g.library': 'Library',
    'exp.g.libraryT': 'Books, boards and beach vibes.',
    'exp.g.bbq': 'Barbecue',
    'exp.g.bbqT': 'Outdoor meals and hangouts.',
    'exp.g.solarium': 'Solarium',
    'exp.g.solariumT': 'Sun, reading and the pool nearby.',
    'exp.g.bora': 'Bora Beer',
    'exp.g.boraT': 'The hostel bar, right at home.',
    'exp.g.reception': 'Reception',
    'exp.g.receptionT': 'Dune tips, check-in and good vibes.',
    'exp.g.terrace': 'Terraces',
    'exp.g.terraceT': 'Pool table and sunsets.',
    'exp.g.night': 'Hostel at night',
    'exp.g.nightT': 'Our colorful facade under the stars.',
    'exp.g.party': 'Vibe',
    'exp.g.partyT': 'Music, pool and community.',
    'exp.g.dunas': 'Dunes',
    'exp.g.dunasT': 'On the way to Cabo Polonio.',
    'exp.g.summer': 'Summer',
    'exp.g.summerT': 'Floats, sun and staying longer.',
  },
  pt: {
    'exp.g.pool': 'Piscina',
    'exp.g.poolT': 'Sol, espreguiçadeiras e água cristalina.',
    'exp.g.heated': 'Piscina climatizada',
    'exp.g.heatedT': 'Para aproveitar também em dias frescos.',
    'exp.g.rooms': 'Quartos',
    'exp.g.roomsT': 'Privados e compartilhados.',
    'exp.g.coliving': 'Cool Living',
    'exp.g.colivingT': 'Espaços para conectar, trabalhar e compartilhar.',
    'exp.g.library': 'Biblioteca',
    'exp.g.libraryT': 'Livros, pranchas e vibe de praia.',
    'exp.g.bbq': 'Churrasqueira',
    'exp.g.bbqT': 'Encontros ao ar livre.',
    'exp.g.solarium': 'Solário',
    'exp.g.solariumT': 'Sol, leitura e piscina por perto.',
    'exp.g.bora': 'Bora Beer',
    'exp.g.boraT': 'O resto bar do hostel.',
    'exp.g.reception': 'Recepção',
    'exp.g.receptionT': 'Dicas de dunas e boa vibração.',
    'exp.g.terrace': 'Terraços',
    'exp.g.terraceT': 'Sinuca e pores do sol.',
    'exp.g.night': 'Hostel à noite',
    'exp.g.nightT': 'A fachada colorida sob as estrelas.',
    'exp.g.party': 'Ambiente',
    'exp.g.partyT': 'Música, piscina e comunidade.',
    'exp.g.dunas': 'Dunas',
    'exp.g.dunasT': 'Caminho a Cabo Polonio.',
    'exp.g.summer': 'Verão',
    'exp.g.summerT': 'Boias, sol e vontade de ficar.',
  },
}

for (const lang of ['es', 'en', 'pt']) {
  Object.assign(patches[lang], galleryKeys[lang])
}

function patchSection(text, startToken, endToken, dict) {
  const start = text.indexOf(startToken)
  const end = text.indexOf(endToken, start + startToken.length)
  if (start < 0 || end < 0) throw new Error('missing section ' + startToken)
  let section = text.slice(start, end)
  for (const [key, value] of Object.entries(dict)) {
    const re = new RegExp(`'${key.replace(/\./g, '\\.')}':\\s*(?:'(?:\\\\'|[^'])*'|"(?:\\\\"|[^"])*")`)
    const replacement = `'${key}': ${JSON.stringify(value)}`
    if (re.test(section)) section = section.replace(re, replacement)
    else section += `\n    ${replacement},`
  }
  return text.slice(0, start) + section + text.slice(end)
}

s = patchSection(s, '  es: {', '\n\n  en: {', patches.es)
s = patchSection(s, '\n\n  en: {', '\n\n  pt: {', patches.en)
s = patchSection(s, '\n\n  pt: {', '\n  },\n}', patches.pt)

fs.writeFileSync(path, s)
console.log('ok')
