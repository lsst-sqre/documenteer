const { resolve } = require('path');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');

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
  plugins: [new MiniCssExtractPlugin({ filename: 'styles/[name].css' })],
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
