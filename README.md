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


## Entrega de los Hitos
### Hito 1
El código está disponible en la rama [`hito/1`](../../tree/hito/1) y su documentación en [Documentación Hito 1](./docs/Hito1.md)






