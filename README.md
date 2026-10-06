# Prácticas de Cloud Computing
### Por Natalia Serrano Cerceda

La aplicación pretende ser una web online de preguntas tipo Trivial. Ofreciendo rondas de 10 preguntas de distintas categorías, dificultad y formato. 
Asimismo, cada jugador dispondrá de unas estadísticas personalizadas reflejando su progreso en el juego.

Está aplicación está orientada para el desarrollo en la nube porque no cuenta con un patrón de uso constante, funcionando con picos de tráfico en tiempo real 
y requiere un procesamiento diferenciado entre jugar y consultar datos. 

Cuenta con dos microservicios, uno manejando las partidas y otro gestionando las cuentas de usuario y sus estadísticas.

## Justificación NIST SP 800-145
#### - Autoservicio bajo demanda:
#### - Acceso amplio a la red: 
#### - Asignación común de recursos: 
#### - Rápida elasticidad: 
Al conectarse más jugadores simultáneamente, el microservicio se autoescala automáticamente para soportar las peticiones concurrentes. Al terminar una partida, las instancias se borran automáticamente para no malgastar recursos.
#### - Servicio medido:
El consumo de infraestructura se supervisa y factura en tiempo real en base al uso exacto según el número de peticiones HTPPS, tiempo de cómputo en CPU por partida y gigabytes de datos transferidos. Así, es medible cuanto cuesta cada partida o usuario activo.

## Mapeo de Actores NIST SP 500-292
#### Consumidor
#### Proveedor
#### Intermediario
#### Auditor
#### Operador
