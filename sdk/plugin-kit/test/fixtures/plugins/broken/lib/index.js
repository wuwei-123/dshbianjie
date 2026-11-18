export const name = 'broken-demo'
export const inject = ['dshbianjie']
export function apply(ctx) {
  ctx.inject(['dshbianjie?'], (ctx) => {
    ctx.dshbianjie.on('a', () => ({ insert: 'x' }))
  })
}
