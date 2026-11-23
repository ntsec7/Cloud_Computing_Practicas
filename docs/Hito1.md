# Documentación del Hito 1

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

## Diagrama de Arquitectura
Se seguirá una arquitectura serverless basada en microservicios, que permitirá reducir la gestión de la infraestructura, facilitar la escalabilidad y la elasticidad de la aplicación, favorecer el desacoplamiento de sus componentes y ajustar los costes al uso de los servicios.  

Se hará uso de los servicios de AWS para desplegar la aplicación en la nube. El navegador se comunicará con CloudFront, que distribuirá el contenido de la página web almacenado en S3, un servicio de almacenamiento de objetos. Asimismo, CloudFront actuará como punto de entrada para las peticiones a la API, redirigiéndolas a API Gateway, que se encargará de encaminarlas a los microservicios correspondientes mediante la configuración de rutas e integraciones. CloudFront permitirá aplicar políticas de caché para mejorar el rendimiento, especialmente en la distribución de contenido estático.  

Los microservicios se implementarán mediante funciones AWS Lambda y se comunicarán con la base de datos para consultar y almacenar la información necesaria. Adicionalmente, el microservicio de Juego se comunicará con la API externa de OpenTDB para obtener las preguntas del Trivial.  

La base de datos será DynamoDB, un servicio de base de datos NoSQL gestionado por AWS. Se ha optado por esta tecnología por su integración con el ecosistema de AWS, su capacidad de escalado y su modelo de facturación, que puede resultar económico para una aplicación de este tamaño si se diseña adecuadamente.  

![Diagrama de Arquitectura](../img/hito1/DiagramaDeArquitectura.png)

## Especificación de la API REST

A continuación, se expone una documentación sintética de los endpoints principales organizados por microservicios.

<ins>Login</ins>

| Método | Ruta | Payload JSON | Descripción |
| --- | --- | --- | --- |
| GET | `/health` | — | Comprobar el estado del microservicio |
| POST | `/auth/register` | `email`, `password`, `username`, `name`, `avatar_id` | Registrar una nueva cuenta |
| POST | `/auth/login` | `email`, `password` | Iniciar sesión |
| GET | `/auth/me` | — *(Requiere Bearer Token)* | Consultar los datos del usuario autenticado |
| PATCH | `/auth/me` | `username`, `name`, `avatar_id`, `email` *(opcionales, Bearer Token)* | Actualizar los datos del usuario autenticado |
| POST | `/auth/change-password` | `previous_password`, `proposed_password` *(Bearer Token)* | Cambiar la contraseña del usuario autenticado |
| POST | `/auth/logout` | — *(Requiere Bearer Token)* | Cerrar sesión |
| DELETE | `/auth/account` | — *(Requiere Bearer Token)* | Eliminar la cuenta del usuario autenticado |
| GET | `/admin/users/<user_id>` | — *(Requiere Bearer Token de admin)* | Consultar los datos de un usuario (Admin) |
| PATCH | `/admin/users/<user_id>` | Campos a actualizar *(Bearer Token de admin)* | Modificar los datos de un usuario (Admin) |
| PATCH | `/admin/users/<user_id>/password` | `new_password` *(Bearer Token de admin)* | Cambiar la contraseña de un usuario (Admin) |
| DELETE | `/admin/users/<user_id>` | — *(Requiere Bearer Token de admin)* | Eliminar cualquier cuenta de usuario (Admin) |

<ins>Profile</ins>
| Método | Ruta | Payload JSON | Descripción |
| --- | --- | --- | --- |
| GET | `/profile/health` | — | Comprobar el estado del microservicio de perfil |
| POST | `/profile` | `user_id`, `username`, `name`, `avatar_id` *(Requiere X-Internal-Token)* | Crear un nuevo perfil de usuario |
| GET | `/profile/<user_id>` | — *(Requiere X-Internal-Token)* | Consultar los datos de un perfil |
| PATCH | `/profile/<user_id>` | `username`, `name`, `avatar_id` *(opcionales, X-Internal-Token)* | Actualizar los datos de un perfil |
| DELETE | `/profile/<user_id>` | — *(Requiere X-Internal-Token)* | Eliminar un perfil |
| PATCH | `/profile/<user_id>/admin` | `username`, `name`, `avatar_id`, `role` (`client` \| `admin`) *(opcionales, X-Internal-Token)* | Actualizar un perfil incluyendo su rol (Admin) |

<ins>Game</ins>
| Método | Ruta | Payload JSON | Descripción |
| --- | --- | --- | --- |
| GET | `/game/health` | — | Comprobar el estado del microservicio |
| POST | `/game/` | `category` *(int, opcional)*, `difficulty` (`easy` \| `medium` \| `hard`, *opcional*) *(Bearer Token)* | Crear una nueva partida |
| POST | `/game/<game_id>/answer` | `question_id` *(str)*, `answer` *(int)* *(Bearer Token)* | Enviar la respuesta a una pregunta de la partida |
| GET | `/game/internal/games/<game_id>` | — *(Requiere X-Internal-Token)* | Recuperar los datos de una partida para estadísticas |
| GET | `/game/internal/games/<game_id>/responses` | — *(Requiere X-Internal-Token)* | Recuperar las respuestas de una partida para estadísticas |
| GET | `/game/internal/users/<user_id>/responses` | — *(Requiere X-Internal-Token)* | Recuperar todas las respuestas de un usuario para estadísticas |

<ins>Statistics</ins>
| Método | Ruta | Payload JSON | Descripción |
| --- | --- | --- | --- |
| GET | `/statistics/health` | — | Comprobar el estado del microservicio de estadísticas |
| GET | `/statistics/game/<game_id>` | — *(Requiere Bearer Token)* | Consultar las estadísticas de una partida (propietario o admin) |
| GET | `/statistics/user/<user_id>` | — *(Requiere Bearer Token)* | Consultar las estadísticas totales de un usuario (propio usuario o admin) |
