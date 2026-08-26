**Status: DEFERRED** — Not required for MVP. Prerequisites (georeferenced landing ports, validated allometric relationship) are not yet met. Revisit after CONAPESCA port cleanup is complete.

---

# Contexto: Skill de Esfuerzo Pesquero Predicho (PFE)

## Estado
Propuesta metodológica. Pendiente de implementación cuando la base de datos esté limpia.

## Qué queremos estimar
La distribución espacial del esfuerzo pesquero artesanal usando el método de
**Johnson et al. (2017)** *A spatial method to calculate small-scale fisheries
effort in data poor scenarios. PLoS ONE 12(4): e0174064.*

La métrica central es el **Esfuerzo Pesquero Predicho (PFE)**:

```
PFE = (barcos × población^0.43)^0.5
```

Unidad: número de embarcaciones ajustado por población costera, por celda de 500 km² por día.

---

## Resumen del método original (Johnson et al. 2017)

1. **Datos de población**: censo INEGI, localidades dentro de 5 km de la costa, georeferenciadas por comunidad.
2. **Datos de embarcaciones**: conteo de pangas por localidad costera, georeferenciadas.
3. **Área de influencia**: buffer de 75 km lineales desde la costa (radio de pesca promedio en el Alto Golfo, validado con rastreos GPS) + isobata de 200 m.
4. **Grilla**: celdas de 500 km² dentro del área de influencia (565 celdas en el Golfo de California).
5. **KDE**: Kernel Density Estimation (kernel cuadrático de Epanechnikov, radio h = 75 km) aplicado por separado a población y embarcaciones para distribuir los valores a todas las celdas.
6. **Relación alométrica**: verificar que log(barcos) ~ log(población) sea significativa antes de calcular PFE. En el Golfo de California: r² = 0.65, exponente m = 0.43 ± 0.013.
7. **Cálculo del PFE**: media geométrica de barcos observados y barcos predichos por población.
8. **Validación**: comparar PFE contra frecuencia real de eventos de pesca (rastreos GPS, r² = 0.43, ρ = 0.65).
9. **Predicción de capturas**: modelo asintótico `captura = K × e^(-b/PFE)`, K = 2,204 t/500 km²/año, punto de inflexión en ~23.5 barcos/500 km².

---

## Decisiones de adaptación para nuestros datos

### Alcance inicial
- **Región**: Golfo de California únicamente, por ser donde existe el radio de pesca validado (75 km) y el coeficiente alométrico (0.43).
- **Flota**: solo pesca artesanal (MENORES). La flota de altura requiere rangos distintos y tiene VMS disponible por otros métodos.

### Fuente de embarcaciones
- Disponemos de folios CONAPESCA con número de embarcaciones.
- La georreferencia más precisa disponible es el **puerto de desembarque** (no la oficina de pesca del folio).
- Supuesto asumido: para pesca artesanal, el puerto de desembarque coincide típicamente con el puerto de salida. El sesgo residual existe pero es minoritario.
- Los puertos de desembarque se asociarán a su localidad INEGI para cruzar con datos de población.

### Fuente de población
- INEGI, filtrado a localidades costeras dentro de 5 km de la línea de costa.

### Sesgo de asignación espacial conocido
- Usar puerto de desembarque en lugar de ubicación GPS del barco concentra artificialmente el esfuerzo en puertos mayores.
- Alternativa evaluada y descartada para v1: distribuir embarcaciones por oficina de pesca → peor que puerto de desembarque.

---

## Pendientes antes de implementar

- [ ] Limpiar y georreferenciar los puertos de desembarque en los folios CONAPESCA.
- [ ] Confirmar que la relación log(barcos) ~ log(población) es significativa con nuestros datos (puede diferir del exponente 0.43 del paper).
- [ ] Definir fuente del radio de pesca si se extiende fuera del Golfo de California.
- [ ] Decidir si separar por arte de pesca o mantener PFE independiente del tipo de pesquería (como en el paper).
- [ ] Identificar fuente de datos de captura por puerto para la validación (equivalente a CONAPESCA 2001-2013 del paper).
