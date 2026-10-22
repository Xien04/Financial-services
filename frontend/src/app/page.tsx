export default function HomePage() {
  return (
    <section aria-labelledby="welcome-title" className="welcome">
      <p className="eyebrow">Your financial overview</p>
      <h1 id="welcome-title">A clearer view of your money.</h1>
      <p>Keep your accounts, spending, and plans together in one private place.</p>
      <div className="notice" role="note">
        <h2>We’re getting things ready</h2>
        <p>Account setup and transaction tracking are coming next.</p>
      </div>
    </section>
  );
}
