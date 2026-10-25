<!--
  Spanish version of content/about.md (the About page). Same rules as that file.
  "Use of AI tools" shows the English text from content/about.md automatically (the "= Use of AI tools" at the end of
  its heading), so the team's own words appear in every language. Translated with AI help: please have a native
  speaker review it.
-->

# Acerca de HomeKeep

Una casa es lo más grande que la mayoría de las familias deja como herencia. En Columbus, muchas familias pierden esa
riqueza no por deudas ni por un mal negocio, sino porque nunca se presentó un formulario. Creamos HomeKeep para que
cualquier familia pueda averiguar, en lenguaje sencillo y gratis, si su casa está protegida y qué hacer después.

## Para quién es {heart}

Para dueños de casa, sobre todo personas mayores, y familias que heredaron una casa. Está escrito para personas que
nunca han hablado con un abogado, funciona en el celular y tiene un botón para agrandar la letra.

## Por qué importa aquí {users}

Las propiedades de herederos se concentran en vecindarios que sufrieron años de falta de inversión, donde las familias
tenían menos acceso a abogados y a planificación de herencias (Greater Ohio Policy Center, 2024). Un título claro es lo
que le permite a una familia conseguir préstamos para reparaciones, ayuda por desastres y la reducción de impuestos de
vivienda, y pasar la casa a la siguiente generación.

## Cómo funciona {map}

1. Usted escribe una dirección. La aplicación consulta los registros públicos de parcelas del Auditor del Condado de
   Franklin (un servicio ArcGIS REST) para ver quién está en la escritura y cuándo cambió de dueño por última vez.
2. Usted contesta unas preguntas de sí o no, por ejemplo si todas las personas en la escritura están vivas.
3. Reglas basadas en la ley de Ohio (declaraciones juradas de Transferencia en caso de Muerte, escrituras con derecho
   de supervivencia y las opciones para patrimonios pequeños de la Corte de Sucesiones del Condado de Franklin)
   convierten las respuestas en un resultado, un resumen en lenguaje sencillo escrito para usted, y un plan de pasos
   con tiempo, costo y adónde ir en cada paso.
4. La revisión opcional de beneficios de vivienda calcula el ahorro en impuestos de propiedad para el distrito de
   impuestos de la casa, usando las cifras publicadas por el Auditor del Condado, y explica cómo y cuándo solicitarlo.
5. "¿Quién heredaría?" muestra cómo la ley de Ohio dividiría la casa, y cuántos dólares de riqueza familiar quedan
   bloqueados hasta que todos los herederos firmen.
6. "Ayuda gratis cerca de usted" muestra en un mapa las oficinas gratis y oficiales que se encargan de cada paso.
7. Toda la aplicación está disponible en inglés, español y somalí.

## Privacidad y seguridad desde el diseño {shield}

- Una dirección a la vez. La aplicación nunca hace listas ni mapas de casas que podrían tener títulos enredados,
  porque las personas que se aprovechan de las propiedades de herederos podrían usarlos mal.
- Los vecinos en el mapa solo muestran lo que el mapa público del Condado ya muestra, nunca el estado de un título.
- Nada de lo que escribe se guarda. El servidor no guarda nada entre un clic y otro. Las marcas de su plan de pasos
  se quedan en su propio dispositivo.

## Límites {info}

- Información general, no es consejo legal. Cada plan le indica dónde conseguir ayuda legal gratis.
- Solo el Condado de Franklin (por ahora). Los registros del Condado pueden tardar en mostrar trámites recientes.
- La aplicación no puede saber si alguien murió; se lo pregunta a usted. Los ahorros son cálculos del Auditor.

## Hecho por {users}

- **Tejas Menneni**, New Albany High School, 12.º grado
- **Satvik Surapaneni**, Olentangy High School, 12.º grado
- **Sutton Sykes**, New Albany High School, 12.º grado
- **Naman Soni**, Olentangy High School, 12.º grado

## Hecho con {file}

Python, HTML / CSS / JavaScript y pytest, alojado en Vercel.
Mapas de los colaboradores de OpenStreetMap y Esri World Imagery.
Datos de parcelas y cálculos de vivienda del Auditor del Condado de Franklin.
La letra es Atkinson Hyperlegible.

## Uso de herramientas de IA {info} = Use of AI tools
