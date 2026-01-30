describe('Landing Zone Portal E2E Tests', () => {
  it('should load the homepage', () => {
    cy.visit('/')
    cy.contains('Landing Zone Portal').should('be.visible')
  })
})