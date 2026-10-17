# AUTONOMOUS_RUN_F6 — corrida autónoma: contrastes pendientes con flow5, M25, M26 y paquete de traspaso

Este archivo manda sobre cualquier otra instrucción de la corrida, salvo `CLAUDE.md` y las instrucciones maestras del proyecto. Las reglas de autonomía, parada, git, cierre, fuentes y "sin simulaciones falsas" de `AUTONOMOUS_RUN_F5.md` (y de las anteriores) siguen vigentes en lo que no contradiga este archivo; aquí se repiten las esenciales.

## 1. Alcance y orden
Fase F6 de Gudmundsson (pasos 25-27: V-n, cargas, diseño preliminar) más los contrastes con flow5 que F4 y F5 dejaron pendientes. Orden:

1. **P-1** Fuselaje en flow5 y contraste de M16 con cuerpo (§2).
2. **P-2** Investigación del fallo de LLT en flow5 7.55 (§3).
3. **P-3** Derivadas laterales y modos de M16 contra flow5 tipo 7; distribución C_l(η) de M19 contra flow5 (§4).
4. **M25** Envolvente V-n (paso 25; §5).
5. **M26** Cargas aerodinámicas para Ansys (paso 26; §6).
6. **P-4** Optimización con acople de peso del ala (§7).
7. **P-5** M23: textos normativos pendientes (§8).
8. **T-1** Paquete de traspaso del diseño preliminar (paso 27; §9).
9. **V-1** Actualización de `VERIFICAR.md` (§10).

Fuera de alcance: dimensionamiento estructural, FEA, aeroelasticidad, CFD, interfaz gráfica y todo lo que `ARCHITECTURE.md` marca como fuera de alcance.

## 2. P-1: fuselaje en flow5 y contraste de M16
Hallazgo de F5: el modelo de flow5 de la evidencia no tiene fuselaje, por eso el aporte del fuselaje de M16 (Munk-Multhopp, Ecs. 24-100 a 24-108) solo se validó con el Ejemplo 24-3 del libro; y el contraste con flow5 sin fuselaje sigue en +5.3 % de punto neutro (0.695 m contra 0.66 m), +11.8 % de C_Mα, es decir, M16 es menos conservador que flow5 en ese caso.
1. Amplía `aerosuite/flow5_xml.py` para exportar un cuerpo (fuselaje) como lo define el XML de flow5 7.55: lee el código fuente de `vendor/flow5` para el formato del cuerpo (no dependas de la interfaz gráfica: usa lo que define el XML del código fuente y comprueba que flow5 7.55 lo acepte). Sin modificar `vendor/`.
2. Si flow5 acepta el cuerpo, ejecuta el avión de `examples/flow5-c162-like.json` con fuselaje (VLM2, 300 s máx.), guarda las salidas reales en `evidence/flow5-7.55-win/fuselage/` y compara con M16 con fuselaje: punto neutro, margen estático, C_Mα. Informa las diferencias con cifras antes y después; no ajustes constantes para igualar a flow5.
3. Comprueba además, con una prueba de regresión, que el signo corregido en F5 solo afecta al término del fuselaje: sin fuselaje M16 debe seguir dando el punto neutro previo (0.695 m en el caso de contraste).
4. Si flow5 no acepta o no resuelve el cuerpo (error de ensamblado de panel, modo por lotes), registra la evidencia del intento y deja el contraste con fuselaje como BLOQUEADO, sin alterar M16.
5. Estudia el modelo de estela de M16 (∂ε/∂α = 0.39) frente al VLM2: ejecuta flow5 con la cola a distintas alturas o desplazamientos y mide ε en la cola si los resultados lo permiten; informa si la diferencia de +5.3 % es explicable por la interferencia ala-cola. Es solo diagnóstico, sin cambiar M16 salvo que una fuente del libro lo respalde.
6. Commit: `feat(P-1): fuselaje en flow5 y contraste de M16`.

## 3. P-2: LLT de flow5 7.55
En F5, LLT con el ala de M09b terminó "con errores" y 0 puntos (`LLT analysis completed ... Errors encountered`; Dirichlet, masa 0).
1. Reproduce el fallo y registra el mensaje exacto de flow5.
2. Revisa en `vendor/flow5` qué condiciones exige LLT (polares de perfil asociadas, número de estaciones, rango de α, masa, condiciones de Reynolds). Prueba variantes razonables del XML (polares de perfil precalculadas con XFOIL de AeroSuite, otro rango de α, masa explícita). Tiempo máximo de 300 s por corrida; no toques la instalación de flow5.
3. Si LLT funciona, guarda la evidencia, ajusta `flow5_xml.py` y compara la polar con VLM2 y con la línea sustentadora de M19. Si no, deja documentado el diagnóstico y que LLT no es utilizable con 7.55 en modo por lotes.
4. Commit: `feat(P-2): diagnóstico y soporte de LLT en flow5 7.55`.

## 4. P-3: contrastes de M16 y M19 con flow5
1. **M16 dinámica:** ejecuta una polar de estabilidad (tipo 7) del avión de ejemplo con flow5, lee derivadas y modos con M-F5R y compáralos con M16 (fugoide, periodo corto, balanceo holandés, espiral, convergencia en balanceo). flow5 usa inercia de masa puntual: declara esa diferencia y, si hace falta, ejecuta M16 con la misma inercia para que la comparación sea consistente. Informa diferencias con cifras.
2. **M19 distribución C_l(η):** los puntos de operación de flow5 (`PlaneOpp::exportMainDataToString` y las tablas por estación que M-F5R ya lee) incluyen C_l por estación. Genera esos archivos con flow5 7.55 (exportación de puntos de operación) y compara con la distribución de la línea sustentadora de M19 a los mismos ángulos, y con el avance de la pérdida cuando haya datos de perfil. Informa diferencias con cifras.
3. Si algún archivo de salida difiere del formato esperado por M-F5R, corrige el lector (tolerante a 7.55 y 7.57) con una prueba de regresión que use el archivo real de `evidence/`.
4. Commit: `feat(P-3): contrastes de M16 dinámica y M19 con flow5`.

## 5. M25: envolvente V-n (paso 25)
1. Fuentes: Gudmundsson (capítulo de cargas y envolvente de maniobra y ráfaga; verifica sección y capítulo en el libro: `ARCHITECTURE.md` cita Sec. 17.4 sin comprobar), 14 CFR Part 23 (cargas de vuelo, sin inventar umbrales), y ADRpy solo si ofrece algo en la versión instalada.
2. Entradas del proyecto: pesos de M06/M12, S, CL_max (con y sin flaps, M18c), pendiente de sustentación (M09b), velocidades características (M21). Salidas: velocidades de maniobra, crucero de diseño, picada y pérdida; factores de carga límite y últimos; líneas de ráfaga; polígono de la envolvente; puntos de esquina.
3. Validación numérica con un ejemplo resuelto del libro; si no hay ejemplo, contra cálculo independiente y dilo.
4. Comando `m25`, `export --module m25`, marca de "desactualizado". Commit: `feat(M25): envolvente V-n`.

## 6. M26: cargas aerodinámicas para Ansys (paso 26)
Objetivo del usuario: lo conceptual pasa a Ansys. Aquí solo se generan cargas aerodinámicas externas sobre la geometría exterior; sin estructura.
1. Condiciones: los puntos de esquina de M25 (n límite en cada velocidad), con peso, CG e inercias de M12/M13.
2. Cargas por condición: sustentación, resistencia y momento totales; distribución en envergadura (y, cuerda, C_l, fuerza por estación, cortante y flector de la sección) calculada con la línea sustentadora de M19 y, si la corrida de flow5 está disponible para esa condición, con la distribución de flow5 (VLM2) leída con M-F5R. Declara de cuál proviene cada resultado.
3. Cargas de inercia y equilibrio: factor de carga, aceleraciones y fuerzas de inercia a partir de la distribución de pesos; equilibrio de fuerzas y momentos con la cola. No inventes alivio estructural.
4. Exportación para Ansys: CSV y JSON con sistema de ejes, unidades SI y el mismo sistema de coordenadas del STEP de M24 (indica la transformación mm-m), una tabla de fuerzas por estación aplicable como cargas puntuales o distribuidas y un manifiesto con versiones, condición de vuelo y trazabilidad. No generes archivos de entrada propios de Ansys (APDL, Workbench) salvo que su formato esté documentado públicamente y puedas citarlo; en ese caso solo texto simple y sin ejecutar nada.
5. Validación: equilibrio (la suma de fuerzas de las estaciones iguala la sustentación total) y comparación con las cifras del Ejemplo del libro cuando exista; contraste con flow5 cuando haya datos.
6. Comando `m26`, `export --module m26`. Commit: `feat(M26): cargas aerodinámicas para Ansys`.

## 7. P-4: optimización con acople de peso
F5 dejó M22 sin un modelo de peso que contrarreste el alargamiento (D-07): el alargamiento optimiza hacia el límite. 
1. Haz que el motor `project` de M22 pueda variar la geometría del ala (AR, S, λ) con el peso del ala de M12 recalculado en cada evaluación, para que haya un óptimo interior. Si M12 ya depende de la geometría del ala, basta con definir las variables y métricas; si no, añade la dependencia con las ecuaciones de peso del libro (Cap. 6) ya implementadas, sin inventar relaciones.
2. Ejemplo en `examples/` y validación contra barrido de malla con el óptimo interior; informa las diferencias de DE y SLSQP con el barrido. Declara el nivel (conceptual) y que no es optimización aerodinámica 3D.
3. Commit: `feat(M22): acople de peso del ala y ejemplo con óptimo interior`.

## 8. P-5: M23 con textos normativos pendientes
F5 dejó `no evaluable` los apartados cuyo texto no se pudo leer (23.2135/2145/2150, ascenso frustrado y gradiente en configuración de ascenso inicial, CS-23).
1. Intenta leer el texto vigente del eCFR (versión actual de 14 CFR Part 23; las versiones históricas devolvieron 404) y, si es accesible, EASA CS-23 e ISO/ASTM públicos. Solo se admiten fuentes públicas; no uses documentos protegidos.
2. Implementa solo las verificaciones cuyo texto hayas leído y citado (con apartado y enmienda). Lo demás sigue `no evaluable` con la razón.
3. Pruebas con casos en el umbral, por debajo y por encima. Commit: `feat(M23): apartados adicionales con texto normativo verificado`.

## 9. T-1: paquete de traspaso (paso 27)
1. Comando `python -m aerosuite handoff --project proyecto.json --out paquete/` que reúna, sin copiar libros ni binarios de terceros: el `project.json` con trazabilidad; el STEP de M24; las cargas de M26; pesos, CG e inercias (M12/M13); la envolvente V-n; el informe de requisitos de M23; la lista de supuestos y de módulos sin validación; la nota de costos de 2012 si hay costos; un `LEEME.md` en español y un manifiesto con versiones y SHA-256.
2. Prueba de integración con el ejemplo de proyecto completo. Commit: `feat(T-1): paquete de traspaso de diseño preliminar`.

## 10. V-1: actualiza `VERIFICAR.md`
Añade los módulos y contrastes nuevos con su estado de validación, las 1 a 3 comprobaciones por módulo en el libro del usuario (ecuación, página impresa, cifra esperada) y los comandos, y actualiza la lista de supuestos y erratas. Incluye un apartado "abrir el STEP en SolidWorks y en Ansys" con comprobaciones de unidades (milímetros), orientación de ejes y sólidos válidos. Commit: `docs: VERIFICAR actualizado para F6`.

## 11. Reglas especiales (heredadas)
- **Ecuaciones ilegibles:** reconstrúyelas desde la deducción del libro y verifícalas con un ejemplo resuelto; si no se puede, dato de entrada marcado como supuesto. Nunca inventes una ecuación.
- **Fuentes, en orden:** carpeta `BIBLIOGRAFIA` local, libros del proyecto, fuentes públicas verificables.
- **Costos:** cualquier resultado con costo lleva la nota de 2012 (D-23).
- **flow5 y XFOIL:** rutas configuradas (`AEROSUITE_FLOW5`, `AEROSUITE_XFOIL`); el flow5 instalado es 7.55 (el código fuente es 7.57). Tiempo máximo de 300 s por corrida; no toques su instalación. Con la sesión de Windows bloqueada flow5 puede fallar; registra el síntoma sin interpretarlo como fallo del motor.
- **Sin factor de seguridad** sobre el margen estático ni penalizaciones físicas inventadas.
- Las salidas reales de flow5/XFOIL van en `evidence/` rotuladas con versión y comando; los fixtures de formato no se mezclan con ellas.
- No modifiques `vendor/`. CadQuery ya está instalado con `--no-deps` (D-49); no instales nada más fuera de `requirements-core.txt` y `requirements-cad.txt`.

## 12. Autonomía y parada
Nadie responde durante la corrida: no hagas preguntas. Ante una duda técnica elige la opción más simple que respete a Gudmundsson y a las fuentes primarias, regístrala en `DECISIONS.md` (continúa la numeración desde la última D-xx; la última conocida es D-49) y sigue. Detén una tarea, anótala BLOQUEADA y pasa a la siguiente solo si: requiere modificar `vendor/`, borrar archivos validados o reescribir historia de git; la ecuación necesaria no se puede comprobar en ninguna fuente y no hay dato de entrada posible; o una prueba falla tres intentos seguidos por la misma causa. Las tareas con flow5 se limitan a lo que el ejecutable acepte en modo por lotes; un fallo del motor no justifica cambiar los módulos para ocultar la diferencia.

## 13. Git
- Rama de trabajo: `auto/f6`. Antes de crearla ejecuta `git fetch` y `gh pr list --head auto/f5 --state all --json number,state`:
  - si el PR de `auto/f5` está `MERGED`, crea `auto/f6` desde `origin/main`;
  - si no, crea `auto/f6` desde `auto/f5` (el PR final incluirá esos commits y lo dirás en su descripción).
  Si `auto/f6` ya existe, continúa en ella.
- Los cambios sin confirmar de `AUTONOMOUS_RUN_F6.md` e `INICIAR-AUTONOMO.cmd` van en el primer commit: `chore: plan de la corrida F6`. `PR_*.md` y `tools/` siguen sin versionarse.
- Un commit por tarea y `git push` de la rama tras cada commit. Nunca `--force`, nunca a `main`, nunca fusiones el PR.
- Si `git push` falla por credenciales, usa `gh auth git-credential` como ayudante de una sola ejecución, sin cambiar la configuración global.
- Tras cada tarea actualiza `PROJECT_STATE.md`, `TEST_RESULTS.md`, `DECISIONS.md`, `CLAUDE_HANDOFF.md` y `ROADMAP.md`. Usa `.venv\Scripts\python` y ejecuta toda la suite antes de cada commit.

## 14. Bitácora de la corrida
La corrida puede reiniciarse varias veces. Al empezar, lee esta sección y retoma donde quedó. Al terminar cada tarea o al detenerte añade una línea:
`- AAAA-MM-DD HH:MM | tarea | TERMINADO / EN CURSO / BLOQUEADO | commit | nota breve`

- 2026-10-16 19:30 | P-1 | TERMINADO | ver git log | cuerpo aceptado por flow5; incremento de fuselaje contrastado (TRILINEAR); hallazgo: la deriva del modelo era horizontal (D-52), contraste estático de M16 −1.2 %
- 2026-10-16 20:10 | P-2 | TERMINADO | ver git log | LLT funciona si flow5 calcula antes las polares 2D del perfil (D-51); contraste con VLM2 y M19
- 2026-10-16 22:00 | P-3 | TERMINADO | ver git log | tipo 7 con inercia de masas puntuales; M16 y M19 contrastados (D-53); lector con polares 2D
<!-- BITACORA -->

## 15. Cierre (dispara el correo)
Cuando todas las tareas de §1 estén TERMINADAS o BLOQUEADAS:
1. Push final de `auto/f6`.
2. Escribe `PR_F6.md` (no se versiona) con: qué se implementó, qué se validó con cifras contra el libro, qué se validó con flow5 y XFOIL reales (versión 7.55 declarada), el resultado del contraste de M16 con y sin fuselaje, qué quedó como supuesto, qué quedó pendiente o bloqueado y la lista de elementos que el usuario debe verificar (apunta a `VERIFICAR.md`).
3. `gh pr create --base main --head auto/f6 --title "[FASE COMPLETA] F6: M25, M26, traspaso y contrastes con flow5" --body-file PR_F6.md`. Si todo lo pendiente quedó BLOQUEADO, el título es `[BLOQUEADO] F6`.
4. Crea el archivo `FASE_COMPLETA.flag` en la raíz (ignorado por git).
