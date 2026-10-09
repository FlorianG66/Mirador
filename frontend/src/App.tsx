// Point de montage des routes de l'application.
import { createBrowserRouter, RouterProvider } from 'react-router'
import { routes } from './app/routes.tsx'

const router = createBrowserRouter(routes)

export default function App() {
  return <RouterProvider router={router} />
}
