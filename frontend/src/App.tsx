import { AuthProvider, useAuth } from "./auth";
import { I18nProvider } from "./i18n";
import { Login } from "./pages/Login";
import { AppShell } from "./shell/AppShell";
import { Icon } from "./components/Icons";

function Splash() {
  return (
    <div className="splash">
      <div className="splash-mark"><Icon name="logo" size={30} /></div>
      <div className="splash-name">intel<span className="accent">2</span>doc</div>
      <span className="spinner big" />
    </div>
  );
}

function Gate() {
  const { user, ready } = useAuth();
  if (!ready) return <Splash />;
  return user ? <AppShell /> : <Login />;
}

export function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <Gate />
      </AuthProvider>
    </I18nProvider>
  );
}
