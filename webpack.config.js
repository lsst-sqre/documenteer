const { resolve, join } = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const CopyPlugin = require('copy-webpack-plugin');

// Directory in the installed rubin-stule-dictionary where assets, such as
// images like logos and favicons, as available.
const rsdAssetsDir = resolve(
  __dirname,
  'node_modules/@lsst-sqre/rubin-style-dictionary/assets/'
);

module.exports = {
  mode: 'development',
  devtool: 'source-map',
  entry: {
    'rubin-technote': [
      './src/assets/rubin-technote/styles/rubin-technote.scss',
    ],
  },
  output: {
    filename: 'scripts/[name].js',
    path: resolve(__dirname, 'src/documenteer/assets'),
  },
  plugins: [
    new MiniCssExtractPlugin({ filename: '[name].css' }),
    new CopyPlugin({
      // Copy assets from Rubin Style Dictionary into
      // src/documenteer/assets/rsd-assets/
      patterns: [
        {
          from: join(
            rsdAssetsDir,
            'rubin-imagotype/rubin-imagotype-color-on-black-crop.svg'
          ),
          to: 'rsd-assets',
        },
        {
          from: join(
            rsdAssetsDir,
            'rubin-imagotype/rubin-imagotype-color-on-white-crop.svg'
          ),
          to: 'rsd-assets',
        },
      ],
    }),
  ],
  optimization: { minimizer: [`...`, new CssMinimizerPlugin()] },
  module: {
    rules: [
      {
        test: /\.(scss|css)$/i,
        use: [
          MiniCssExtractPlugin.loader,
          { loader: 'css-loader', options: { sourceMap: true } },
          { loader: 'postcss-loader', options: { sourceMap: true } },
          { loader: 'sass-loader', options: { sourceMap: true } },
        ],
      },
    ],
  },
};
