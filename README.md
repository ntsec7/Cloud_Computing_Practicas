# Prácticas de Cloud Computing
### Por Natalia Serrano Cerceda

La aplicación pretende ser una web online de preguntas tipo Trivial. Ofreciendo rondas de 10 preguntas de distintas categorías, dificultad y formato. 
Asimismo, cada jugador dispondrá de unas estadísticas personalizadas reflejando su progreso en el juego.

Está aplicación está orientada para el desarrollo en la nube porque no cuenta con un patrón de uso constante, funcionando con picos de tráfico en tiempo real 
y requiere un procesamiento diferenciado entre jugar y consultar datos. 

El sistema está formado por 4 microservicios distintos: logueo, perfil, juego y estadísticas.

#### Estrategia de ramas
- `main :` Versión principal del proyecto
- `feature/* :` Desarrollo de nuevas funcionalidades
- `fix/* :` Corrección de errores
- `hito/<num> :` Versión del código correspondiente a cada entrega para facilitar la corrección


#### Convención de commits semánticos
| Prefijo | Descripción | Ejemplo |
| ---     | ---         |  ---    |
| feat:   | Añadir una nueva funcionalidad | feat: añadido el login |
| fix:    | Corregir un error | fix: bug en la validación del login |
| docs:   | Modificar documentación | docs: añadida Justificación NIST |
| refactor: | Mejorar el código sin cambiar su comportamiento | refactor: mejora de la interfaz |
| test:   | Añadir o modificar pruebas | test: añadidos tests de registro |
| chore:  | Tareas de mantenimiento  | chore: actualizadas dependencias |


## Justificación NIST SP 800-145
- **Autoservicio bajo demanda:**    
La experiencia del usuario no se degrada aunque haya múltiples usuarios a la vez, ya que la nube reacciona inmediatamente asignando más recursos.

- **Acceso amplio a la red:**    
El sistema hace peticiones HTTPS con respuestas JSON. Esto permite que los usuarios puedan jugar o acceder a sus datos desde cualquier dispositivo.

- **Asignación común de recursos:**  
La infraestructura se comparte entre los distintos usuarios mediante multitenancy. Los microservicios operan de forma aislada sobre clústeres gestionados por el proveedor Cloud, asignando recursos físicos de forma dinámica según la carga de trabajo instantánea de la plataforma.

- **Rápida elasticidad:**
Al conectarse más jugadores simultáneamente, el microservicio se autoescala automáticamente para soportar las peticiones concurrentes. Al terminar una partida, las instancias se borran automáticamente para no malgastar recursos.

- **Servicio medido:**  
El consumo de infraestructura se supervisa y factura en tiempo real en base al uso exacto según el número de peticiones HTPPS, tiempo de cómputo en CPU por partida y gigabytes de datos transferidos. Así, es medible cuanto cuesta cada partida o usuario activo.

## Mapeo de Actores NIST SP 500-292
- `Consumidor:` Los clientes de la web
  
- `Proveedor:` La web de Trivial que proporcionamos
  
- `Intermediario:` Hipotéticamente sería una consultora ficticia que nos aconseje sobre qué servicios contratar, comparando precios y nos ayude a gestionar los recursos contratados.
  
- `Auditor:` Hipotéticamente sería una empresa auditora ficticia que nos revisaría la seguridad de la web, la protección de los datos y el cumplimiento de los requisitos.
  
- `Operador:` Las redes de comunicaciones que conectan a los clientes con los datacenters. Ej: Movistar, Vodafone, Telefónica, etc.
