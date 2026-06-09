import CatalogPageComponent from '../components/catalog/CatalogPage';

interface CatalogPageProps {
  onToolViewed?: () => void;
}

export default function CatalogPage({ onToolViewed }: CatalogPageProps) {
  return <CatalogPageComponent onToolViewed={onToolViewed} />;
}
